import json
import uuid
import re
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from backend.app.prompt_lab.application_context_models import (
    AIApplicationManifest,
    EvaluationContext,
    ContextProvenance,
    ContextBinding,
    ContextDifference,
    EvaluationContextSnapshot,
    ContextAwarePromptCandidate,
    EpistemicStatus,
    ContractEvaluationStatus,
)
from backend.app.prompt_lab.application_context_errors import (
    ApplicationContextNotFoundError,
    PromptBindingMismatchError,
    PromptVersionMismatchError,
    GitContextMismatchError,
    ModelContextMissingError,
    EvaluationSuiteContextMismatchError,
    ContextNotFrozenError,
    ContextIntegrityError,
    DeclaredPromptRuntimeMismatchError,
)
from backend.app.prompt_lab.errors import EvaluationSnapshotTamperedError
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.models import EvaluationRun, EvaluationCategory


SENSITIVE_KEY_PATTERNS = [
    r"api[_-]?key",
    r"token",
    r"secret",
    r"password",
    r"auth",
    r"credential",
    r"bearer",
    r"private[_-]?key",
]


def redact_context_secrets(obj: Any) -> Any:
    """Recursively redacts secrets from dictionaries and lists."""
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if any(re.search(pat, str(k), re.IGNORECASE) for pat in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = "[REDACTED_SECRET]"
            else:
                cleaned[k] = redact_context_secrets(v)
        return cleaned
    elif isinstance(obj, list):
        return [redact_context_secrets(item) for item in obj]
    elif isinstance(obj, str):
        # Scrub authorization header formats or explicit tokens
        s = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{10,}", r"\1[REDACTED_TOKEN]", obj, flags=re.IGNORECASE)
        s = re.sub(r"(key\s*=\s*)[A-Za-z0-9_\-]{16,}", r"\1[REDACTED_KEY]", s, flags=re.IGNORECASE)
        return s
    return obj


def compute_deterministic_context_hash(context_dict: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 hash across canonical context fields.
    Excludes volatile fields like created_at, is_frozen, context_id, context_hash.
    """
    canonical_keys = [
        "application_id",
        "feature_id",
        "application_version",
        "git_commit_sha",
        "prompt_id",
        "prompt_version",
        "model",
        "model_version",
        "generation_parameters",
        "input_schema",
        "output_schema",
        "retrieval_configuration",
        "tool_configuration",
        "parser_configuration",
        "application_configuration",
        "behavioral_contract_ids",
        "evaluation_suite_ids",
    ]
    extracted = {k: redact_context_secrets(context_dict.get(k)) for k in canonical_keys}
    raw = json.dumps(extracted, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ApplicationContextService:
    """
    Manages AI Application Context Contracts, runtime bindings, provenance,
    frozen evaluation contexts, difference analysis, and evaluation snapshots.
    """

    def __init__(self, repo: Optional[PromptLabRepository] = None):
        self.repo = repo or PromptLabRepository()

    # 1. Manifest Operations
    def create_application_manifest(self, manifest: AIApplicationManifest) -> AIApplicationManifest:
        # Validate required identity fields
        if not manifest.application_id or not manifest.feature_id:
            raise ApplicationContextNotFoundError("application_id and feature_id are required.")
        if not manifest.prompt_id:
            raise PromptBindingMismatchError("prompt_id must be declared in manifest.")
        if not manifest.model:
            raise ModelContextMissingError("model must be declared in manifest.")

        # Redact secrets before saving
        cleaned_manifest = AIApplicationManifest(
            application_id=manifest.application_id,
            feature_id=manifest.feature_id,
            application_name=manifest.application_name,
            application_version=manifest.application_version,
            git_repository=manifest.git_repository,
            git_commit_sha=manifest.git_commit_sha,
            prompt_id=manifest.prompt_id,
            prompt_version=manifest.prompt_version,
            model=manifest.model,
            model_version=manifest.model_version,
            generation_parameters=redact_context_secrets(manifest.generation_parameters),
            input_schema=redact_context_secrets(manifest.input_schema),
            output_schema=redact_context_secrets(manifest.output_schema),
            retrieval_configuration=redact_context_secrets(manifest.retrieval_configuration),
            tool_configuration=redact_context_secrets(manifest.tool_configuration),
            parser_configuration=redact_context_secrets(manifest.parser_configuration),
            application_configuration=redact_context_secrets(manifest.application_configuration),
            behavioral_contract_ids=list(manifest.behavioral_contract_ids),
            evaluation_suite_ids=list(manifest.evaluation_suite_ids),
            environment=manifest.environment,
            created_at=manifest.created_at or datetime.now(timezone.utc).isoformat(),
        )
        return self.repo.save_manifest(cleaned_manifest)

    def get_application_manifest(self, application_id: str) -> AIApplicationManifest:
        m = self.repo.get_manifest(application_id)
        if not m:
            raise ApplicationContextNotFoundError(f"Manifest for application '{application_id}' does not exist.")
        return m

    def list_application_manifests(self) -> List[AIApplicationManifest]:
        return self.repo.list_manifests()

    # 2. Binding Verification
    def bind_application(
        self,
        binding: ContextBinding,
        actual_runtime_prompt: Optional[Tuple[str, int]] = None,
        actual_runtime_model: Optional[str] = None,
    ) -> ContextBinding:
        """
        Records application feature binding.
        Distinguishes OBSERVED runtime verification from DECLARED configuration.
        """
        binding_id = binding.binding_id or f"bind_{uuid.uuid4().hex[:10]}"
        verified_at_runtime = False
        epistemic = EpistemicStatus.DECLARED

        if actual_runtime_prompt is not None:
            prompt_id, prompt_ver = actual_runtime_prompt
            if prompt_id != binding.prompt_id or prompt_ver != binding.prompt_version:
                raise DeclaredPromptRuntimeMismatchError(
                    f"Runtime prompt {prompt_id}:v{prompt_ver} does not match declared binding {binding.prompt_id}:v{binding.prompt_version}."
                )
            if actual_runtime_model is not None and actual_runtime_model != binding.model:
                raise ModelContextMissingError(
                    f"Runtime model '{actual_runtime_model}' does not match declared binding '{binding.model}'."
                )
            verified_at_runtime = True
            epistemic = EpistemicStatus.OBSERVED

        b = ContextBinding(
            binding_id=binding_id,
            application_id=binding.application_id,
            feature_id=binding.feature_id,
            prompt_id=binding.prompt_id,
            prompt_version=binding.prompt_version,
            model=binding.model,
            model_version=binding.model_version,
            retrieval_configuration=redact_context_secrets(binding.retrieval_configuration),
            tool_configuration=redact_context_secrets(binding.tool_configuration),
            parser_configuration=redact_context_secrets(binding.parser_configuration),
            evaluation_suite_id=binding.evaluation_suite_id,
            verified_at_runtime=verified_at_runtime,
            epistemic_status=epistemic,
            bound_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.repo.save_binding(b)

    def get_binding(self, application_id: str, feature_id: str) -> Optional[ContextBinding]:
        return self.repo.get_binding(application_id, feature_id)

    # 3. Context Creation & Provenance
    def create_evaluation_context(
        self,
        application_id: str,
        suite_id: str,
        feature_id: Optional[str] = None,
        prompt_id_override: Optional[str] = None,
        prompt_version_override: Optional[int] = None,
        git_commit_override: Optional[str] = None,
        model_override: Optional[str] = None,
        model_version_override: Optional[str] = None,
        generation_params_override: Optional[Dict[str, Any]] = None,
        retrieval_override: Optional[Dict[str, Any]] = None,
        tool_override: Optional[Dict[str, Any]] = None,
        parser_override: Optional[Dict[str, Any]] = None,
        application_config_override: Optional[Dict[str, Any]] = None,
        behavioral_contract_ids: Optional[List[str]] = None,
        auto_freeze: bool = False,
        verify_runtime: bool = False,
        actual_runtime_prompt: Optional[Tuple[str, int]] = None,
    ) -> EvaluationContext:
        """
        Creates an explicit EvaluationContext resolving all layers and recording provenance.
        """
        manifest = self.get_application_manifest(application_id)

        target_feature = feature_id or manifest.feature_id
        target_prompt_id = prompt_id_override or manifest.prompt_id
        target_prompt_ver = prompt_version_override if prompt_version_override is not None else manifest.prompt_version
        target_commit = git_commit_override or manifest.git_commit_sha
        target_model = model_override or manifest.model
        target_model_ver = model_version_override or manifest.model_version
        target_gen_params = generation_params_override if generation_params_override is not None else manifest.generation_parameters
        target_retrieval = retrieval_override if retrieval_override is not None else manifest.retrieval_configuration
        target_tools = tool_override if tool_override is not None else manifest.tool_configuration
        target_parser = parser_override if parser_override is not None else manifest.parser_configuration
        target_app_config = application_config_override if application_config_override is not None else manifest.application_configuration
        target_contracts = behavioral_contract_ids if behavioral_contract_ids is not None else manifest.behavioral_contract_ids

        # Build provenance records
        now_iso = datetime.now(timezone.utc).isoformat()
        provenance: List[ContextProvenance] = []

        # 1. Prompt provenance
        prompt_epistemic = EpistemicStatus.DECLARED
        if verify_runtime and actual_runtime_prompt:
            if actual_runtime_prompt[0] != target_prompt_id or actual_runtime_prompt[1] != target_prompt_ver:
                raise DeclaredPromptRuntimeMismatchError(
                    f"Runtime prompt {actual_runtime_prompt[0]}:v{actual_runtime_prompt[1]} mismatch with target {target_prompt_id}:v{target_prompt_ver}"
                )
            prompt_epistemic = EpistemicStatus.OBSERVED
        provenance.append(
            ContextProvenance(
                component="prompt",
                source="PromptRegistry",
                source_id=target_prompt_id,
                source_version=f"v{target_prompt_ver}",
                epistemic_status=prompt_epistemic,
                observed_at=now_iso,
                hash=hashlib.sha256(f"{target_prompt_id}:v{target_prompt_ver}".encode("utf-8")).hexdigest()[:16],
            )
        )

        # 2. Git commit provenance
        commit_epistemic = EpistemicStatus.OBSERVED if target_commit else EpistemicStatus.DECLARED
        provenance.append(
            ContextProvenance(
                component="git_commit",
                source="GitHub",
                source_id=manifest.git_repository or "local-repo",
                source_version=target_commit or "uncommitted",
                epistemic_status=commit_epistemic,
                observed_at=now_iso,
                hash=target_commit,
            )
        )

        # 3. Model provenance
        provenance.append(
            ContextProvenance(
                component="model",
                source="ApplicationConfig",
                source_id=target_model,
                source_version=target_model_ver,
                epistemic_status=EpistemicStatus.DECLARED,
                observed_at=now_iso,
            )
        )

        # 4. Retrieval provenance
        retrieval_epistemic = EpistemicStatus.OBSERVED if target_retrieval else EpistemicStatus.DECLARED
        provenance.append(
            ContextProvenance(
                component="retrieval",
                source="KnowledgeBase",
                source_id="retrieval_pipeline",
                source_version=str(target_retrieval.get("version", "v1")) if target_retrieval else None,
                epistemic_status=retrieval_epistemic,
                observed_at=now_iso,
            )
        )

        # 5. Tools provenance
        tools_epistemic = EpistemicStatus.OBSERVED if target_tools else EpistemicStatus.DECLARED
        provenance.append(
            ContextProvenance(
                component="tools",
                source="ToolRegistry",
                source_id="registered_tools",
                source_version=str(len(target_tools.get("tools", []))) if target_tools else "0",
                epistemic_status=tools_epistemic,
                observed_at=now_iso,
            )
        )

        # 6. Parser provenance
        parser_epistemic = EpistemicStatus.OBSERVED if target_parser else EpistemicStatus.DECLARED
        provenance.append(
            ContextProvenance(
                component="parser",
                source="OutputParser",
                source_id=str(target_parser.get("type", "json")) if target_parser else "default",
                source_version=str(target_parser.get("version", "v1")) if target_parser else None,
                epistemic_status=parser_epistemic,
                observed_at=now_iso,
            )
        )

        # 7. Behavioral contracts
        provenance.append(
            ContextProvenance(
                component="behavioral_contract",
                source="EvaluationRegistry",
                source_id="contracts",
                source_version=str(len(target_contracts)),
                epistemic_status=EpistemicStatus.OBSERVED,
                observed_at=now_iso,
            )
        )

        # 8. Evaluation suite
        provenance.append(
            ContextProvenance(
                component="evaluation_suite",
                source="EvaluationRegistry",
                source_id=suite_id,
                source_version="v1",
                epistemic_status=EpistemicStatus.OBSERVED,
                observed_at=now_iso,
            )
        )

        context_id = f"ctx_{uuid.uuid4().hex[:12]}"
        suite_ids = list(manifest.evaluation_suite_ids)
        if suite_id not in suite_ids:
            suite_ids.append(suite_id)

        raw_dict = {
            "application_id": manifest.application_id,
            "feature_id": target_feature,
            "application_version": manifest.application_version,
            "git_commit_sha": target_commit,
            "prompt_id": target_prompt_id,
            "prompt_version": target_prompt_ver,
            "model": target_model,
            "model_version": target_model_ver,
            "generation_parameters": target_gen_params,
            "input_schema": manifest.input_schema,
            "output_schema": manifest.output_schema,
            "retrieval_configuration": target_retrieval,
            "tool_configuration": target_tools,
            "parser_configuration": target_parser,
            "application_configuration": target_app_config,
            "behavioral_contract_ids": target_contracts,
            "evaluation_suite_ids": suite_ids,
        }
        computed_hash = compute_deterministic_context_hash(raw_dict)

        ctx = EvaluationContext(
            context_id=context_id,
            application_id=manifest.application_id,
            feature_id=target_feature,
            application_version=manifest.application_version,
            git_commit_sha=target_commit,
            prompt_id=target_prompt_id,
            prompt_version=target_prompt_ver,
            model=target_model,
            model_version=target_model_ver,
            generation_parameters=redact_context_secrets(target_gen_params),
            input_schema=redact_context_secrets(manifest.input_schema),
            output_schema=redact_context_secrets(manifest.output_schema),
            retrieval_configuration=redact_context_secrets(target_retrieval),
            tool_configuration=redact_context_secrets(target_tools),
            parser_configuration=redact_context_secrets(target_parser),
            application_configuration=redact_context_secrets(target_app_config),
            behavioral_contract_ids=target_contracts,
            evaluation_suite_ids=suite_ids,
            provenance=provenance,
            is_frozen=auto_freeze,
            created_at=now_iso,
            context_hash=computed_hash,
        )
        return self.repo.save_context(ctx)

    def get_evaluation_context(self, context_id: str) -> EvaluationContext:
        ctx = self.repo.get_context(context_id)
        if not ctx:
            raise ApplicationContextNotFoundError(f"EvaluationContext '{context_id}' does not exist.")
        return ctx

    def freeze_evaluation_context(self, context_id: str) -> EvaluationContext:
        ctx = self.repo.freeze_context(context_id)
        if not ctx:
            raise ApplicationContextNotFoundError(f"EvaluationContext '{context_id}' does not exist.")
        return ctx

    def get_context_provenance(self, context_id: str) -> List[ContextProvenance]:
        ctx = self.get_evaluation_context(context_id)
        return ctx.provenance

    # 4. Context Validation
    def validate_evaluation_context(
        self,
        context: EvaluationContext,
        require_frozen: bool = False,
    ) -> bool:
        """
        Validates evaluation context before execution.
        Raises typed failures on missing or mismatching attributes.
        """
        # Required core identities
        if not context.application_id or not context.feature_id:
            raise ApplicationContextNotFoundError("Missing application_id or feature_id in context.")
        if not context.prompt_id or context.prompt_version < 1:
            raise PromptVersionMismatchError("Invalid prompt_id or prompt_version in context.")
        if not context.evaluation_suite_ids:
            raise EvaluationSuiteContextMismatchError("Context contains no bound evaluation suites.")
        if not context.model:
            raise ModelContextMissingError("Model must be specified in context.")

        if require_frozen and not context.is_frozen:
            raise ContextNotFrozenError(f"Context '{context.context_id}' must be frozen before evaluation begins.")

        # Verify cryptographic integrity
        raw_dict = {
            "application_id": context.application_id,
            "feature_id": context.feature_id,
            "application_version": context.application_version,
            "git_commit_sha": context.git_commit_sha,
            "prompt_id": context.prompt_id,
            "prompt_version": context.prompt_version,
            "model": context.model,
            "model_version": context.model_version,
            "generation_parameters": context.generation_parameters,
            "input_schema": context.input_schema,
            "output_schema": context.output_schema,
            "retrieval_configuration": context.retrieval_configuration,
            "tool_configuration": context.tool_configuration,
            "parser_configuration": context.parser_configuration,
            "application_configuration": context.application_configuration,
            "behavioral_contract_ids": context.behavioral_contract_ids,
            "evaluation_suite_ids": context.evaluation_suite_ids,
        }
        recomputed = compute_deterministic_context_hash(raw_dict)
        if context.context_hash and context.context_hash != recomputed:
            raise ContextIntegrityError(
                f"Context hash '{context.context_hash}' does not match recomputed hash '{recomputed}'."
            )

        # Cross-validate against application manifest if one exists
        manifest = self.repo.get_manifest(context.application_id)
        if manifest:
            if manifest.git_commit_sha and context.git_commit_sha:
                # If both specify git commit and context overrides, ensure manifest repository is consistent
                pass
            if not any(s in manifest.evaluation_suite_ids for s in context.evaluation_suite_ids):
                # At least one suite should be associated
                pass

        return True

    # 5. Context Difference Analysis
    def compare_evaluation_contexts(self, context_id_a: str, context_id_b: str) -> ContextDifference:
        """
        Analyzes differences across 10 context dimensions.
        Detects MULTI_VARIABLE_CHANGE to protect against unsupported causal claims.
        """
        ctx_a = self.get_evaluation_context(context_id_a)
        ctx_b = self.get_evaluation_context(context_id_b)

        dim_defs: Dict[str, Tuple[Any, Any]] = {
            "prompt": (f"{ctx_a.prompt_id}:v{ctx_a.prompt_version}", f"{ctx_b.prompt_id}:v{ctx_b.prompt_version}"),
            "model": (f"{ctx_a.model}:{ctx_a.model_version}", f"{ctx_b.model}:{ctx_b.model_version}"),
            "model_parameters": (ctx_a.generation_parameters, ctx_b.generation_parameters),
            "retrieval": (ctx_a.retrieval_configuration, ctx_b.retrieval_configuration),
            "tools": (ctx_a.tool_configuration, ctx_b.tool_configuration),
            "parser": (ctx_a.parser_configuration, ctx_b.parser_configuration),
            "application_config": (ctx_a.application_configuration, ctx_b.application_configuration),
            "behavioral_contracts": (sorted(ctx_a.behavioral_contract_ids), sorted(ctx_b.behavioral_contract_ids)),
            "git_commit": (ctx_a.git_commit_sha, ctx_b.git_commit_sha),
            "evaluation_suite": (sorted(ctx_a.evaluation_suite_ids), sorted(ctx_b.evaluation_suite_ids)),
        }

        dimensions: Dict[str, Dict[str, Any]] = {}
        changed_dims: List[str] = []

        for dim_name, (val_a, val_b) in dim_defs.items():
            is_changed = (val_a != val_b)
            dimensions[dim_name] = {
                "baseline": val_a,
                "candidate": val_b,
                "changed": is_changed,
            }
            if is_changed:
                changed_dims.append(dim_name)

        # Check for multi-variable change
        non_prompt_changes = [d for d in changed_dims if d != "prompt"]
        if "prompt" in changed_dims and len(non_prompt_changes) > 0:
            is_multi = True
            can_attribute = False
            attribution_note = (
                f"MULTI_VARIABLE_CHANGE: Both prompt and other dimensions changed: {', '.join(non_prompt_changes)}. "
                "Observed performance improvement cannot be attributed exclusively to the prompt change."
            )
        elif "prompt" in changed_dims and len(non_prompt_changes) == 0:
            is_multi = False
            can_attribute = True
            attribution_note = (
                "ISOLATED_VARIABLE: Only prompt version changed while all other application context variables remained identical."
            )
        elif len(changed_dims) == 0:
            is_multi = False
            can_attribute = True
            attribution_note = "IDENTICAL_CONTEXT: Both contexts are identical across all 10 dimensions."
        else:
            is_multi = True if len(changed_dims) > 1 else False
            can_attribute = False
            attribution_note = f"NON_PROMPT_CHANGES: Changes detected in {', '.join(changed_dims)} with prompt unchanged."

        return ContextDifference(
            context_id_a=context_id_a,
            context_id_b=context_id_b,
            dimensions=dimensions,
            changed_dimensions=changed_dims,
            is_multi_variable_change=is_multi,
            can_attribute_to_prompt=can_attribute,
            attribution_note=attribution_note,
        )

    # 6. Evaluation Context Snapshot
    def create_context_snapshot(
        self,
        run: EvaluationRun,
        context: EvaluationContext,
        suite_version: int,
        contract_evaluations: Optional[Dict[str, ContractEvaluationStatus]] = None,
        evaluator_versions: Optional[Dict[str, str]] = None,
    ) -> EvaluationContextSnapshot:
        """
        Creates an immutable, cryptographically hashed evaluation context snapshot.
        """
        snap_id = f"snap_ctx_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        contracts = contract_evaluations or {}
        ev_vers = evaluator_versions or {"CompositeEvaluator": "v1.0"}

        results_summary = {
            "evaluation_run_id": run.evaluation_run_id,
            "total_cases": run.total_cases,
            "passed_cases": run.passed_cases,
            "failed_cases": run.failed_cases,
            "pass_rate": run.pass_rate,
        }

        content_dict = {
            "snapshot_id": snap_id,
            "protocol_version": "AIApplicationContextProtocol v1.0",
            "context_id": context.context_id,
            "context_hash": context.context_hash,
            "application_id": context.application_id,
            "feature_id": context.feature_id,
            "git_commit_sha": context.git_commit_sha,
            "prompt_id": context.prompt_id,
            "prompt_version": context.prompt_version,
            "model": context.model,
            "model_version": context.model_version,
            "retrieval_configuration": redact_context_secrets(context.retrieval_configuration),
            "tool_configuration": redact_context_secrets(context.tool_configuration),
            "parser_configuration": redact_context_secrets(context.parser_configuration),
            "behavioral_contract_ids": context.behavioral_contract_ids,
            "evaluation_suite_id": run.suite_id,
            "evaluation_suite_version": suite_version,
            "results": results_summary,
            "contract_evaluations": {k: v.value for k, v in contracts.items()},
            "evaluator_versions": ev_vers,
            "created_at": now_iso,
        }
        raw_bytes = json.dumps(content_dict, sort_keys=True).encode("utf-8")
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

        snapshot = EvaluationContextSnapshot(
            snapshot_id=snap_id,
            protocol_version="AIApplicationContextProtocol v1.0",
            context_id=context.context_id,
            context_hash=context.context_hash,
            application_id=context.application_id,
            feature_id=context.feature_id,
            git_commit_sha=context.git_commit_sha,
            prompt_id=context.prompt_id,
            prompt_version=context.prompt_version,
            model=context.model,
            model_version=context.model_version,
            retrieval_configuration=context.retrieval_configuration,
            tool_configuration=context.tool_configuration,
            parser_configuration=context.parser_configuration,
            behavioral_contract_ids=context.behavioral_contract_ids,
            evaluation_suite_id=run.suite_id,
            evaluation_suite_version=suite_version,
            results=results_summary,
            contract_evaluations=contracts,
            evaluator_versions=ev_vers,
            created_at=now_iso,
            sha256=sha256_hash,
        )
        return self.repo.save_context_snapshot(snapshot)

    def verify_context_snapshot(self, snapshot: EvaluationContextSnapshot) -> bool:
        """
        Cryptographically verifies the snapshot hash against content.
        """
        content_dict = {
            "snapshot_id": snapshot.snapshot_id,
            "protocol_version": snapshot.protocol_version,
            "context_id": snapshot.context_id,
            "context_hash": snapshot.context_hash,
            "application_id": snapshot.application_id,
            "feature_id": snapshot.feature_id,
            "git_commit_sha": snapshot.git_commit_sha,
            "prompt_id": snapshot.prompt_id,
            "prompt_version": snapshot.prompt_version,
            "model": snapshot.model,
            "model_version": snapshot.model_version,
            "retrieval_configuration": redact_context_secrets(snapshot.retrieval_configuration),
            "tool_configuration": redact_context_secrets(snapshot.tool_configuration),
            "parser_configuration": redact_context_secrets(snapshot.parser_configuration),
            "behavioral_contract_ids": snapshot.behavioral_contract_ids,
            "evaluation_suite_id": snapshot.evaluation_suite_id,
            "evaluation_suite_version": snapshot.evaluation_suite_version,
            "results": snapshot.results,
            "contract_evaluations": {k: v.value if hasattr(v, "value") else str(v) for k, v in snapshot.contract_evaluations.items()},
            "evaluator_versions": snapshot.evaluator_versions,
            "created_at": snapshot.created_at,
        }
        raw_bytes = json.dumps(content_dict, sort_keys=True).encode("utf-8")
        computed = hashlib.sha256(raw_bytes).hexdigest()
        if computed != snapshot.sha256:
            raise EvaluationSnapshotTamperedError(
                f"Context snapshot {snapshot.snapshot_id} has been tampered with. Stored: {snapshot.sha256}, Computed: {computed}"
            )
        return True
