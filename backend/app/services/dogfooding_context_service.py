"""
Slice 8C — Context-Aware Autonomous Dogfooding Service

Orchestrates the integration between:
- Slice 8B: Autonomous Playwright Dogfooding (TestRun, Evidence, Diagnosis, Remediation)
- Slice 7.7.1: AI Application Context Contract (EvaluationContext, Manifest, Provenance)
- Slice 7.8: Human Governance Authorization (can_apply, ChangeAuthorization)

The service binds dogfooding runs to frozen evaluation contexts, performs runtime
verification, runs deterministic evaluators before AI diagnosis, classifies
causal layers with evidence, generates prompt improvement proposals, and
ensures independent retesting with regression detection.
"""

import hashlib
import json
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from backend.app.models.enums import (
    CausalLayer,
    RetestTransition,
    ContractStatus,
    ContextVerificationStatus,
)
from backend.app.models.dogfooding_context import (
    DogfoodingRunContext,
    ComponentVerification,
    AIContextEvidence,
    CausalClassification,
    PromptImprovementCandidate,
    RetestResult,
    RetestComparison,
    compute_config_hash,
)
from backend.app.prompt_lab.application_context_models import (
    EvaluationContext,
    ContextProvenance,
    EpistemicStatus,
)

logger = logging.getLogger("ai_qa_platform.dogfooding_context_service")


class DogfoodingContextService:
    """
    Thin orchestration layer connecting existing subsystems into a unified
    context-aware autonomous dogfooding workflow.

    Does NOT duplicate Prompt Lab, Governance Lab, GitHub lifecycle, or
    Playwright infrastructure — integrates them.
    """

    def __init__(self):
        # In-memory storage for context bindings (integrates with existing repos)
        self._run_contexts: Dict[str, DogfoodingRunContext] = {}
        self._ai_evidence: Dict[str, AIContextEvidence] = {}
        self._causal_classifications: Dict[str, CausalClassification] = {}
        self._prompt_candidates: Dict[str, PromptImprovementCandidate] = {}
        self._retest_results: Dict[str, RetestResult] = {}

    # ─── 1. Context Binding ───────────────────────────────────────────────

    def bind_context_to_run(
        self,
        run_id: str,
        evaluation_context: EvaluationContext,
        evaluation_case_id: Optional[str] = None,
    ) -> DogfoodingRunContext:
        """
        Binds a frozen EvaluationContext to a dogfooding TestRun.
        Computes configuration hashes and creates component verifications.
        The context must be frozen before binding.
        """
        if not evaluation_context.is_frozen:
            raise ValueError(
                f"EvaluationContext '{evaluation_context.context_id}' must be frozen before binding to a dogfooding run."
            )

        # Compute configuration hashes from context
        retrieval_hash = compute_config_hash(evaluation_context.retrieval_configuration)
        tool_hash = compute_config_hash(evaluation_context.tool_configuration)
        parser_hash = compute_config_hash(evaluation_context.parser_configuration)

        # Build initial component verifications from provenance
        verifications = self._build_verifications_from_provenance(
            evaluation_context.provenance
        )

        ctx_binding = DogfoodingRunContext(
            run_id=run_id,
            evaluation_context_id=evaluation_context.context_id,
            context_hash=evaluation_context.context_hash,
            application_id=evaluation_context.application_id,
            feature_id=evaluation_context.feature_id,
            git_commit_sha=evaluation_context.git_commit_sha,
            prompt_id=evaluation_context.prompt_id,
            prompt_version=evaluation_context.prompt_version,
            model=evaluation_context.model,
            model_version=evaluation_context.model_version,
            retrieval_configuration_hash=retrieval_hash,
            tool_configuration_hash=tool_hash,
            parser_configuration_hash=parser_hash,
            behavioral_contract_ids=list(evaluation_context.behavioral_contract_ids),
            evaluation_case_id=evaluation_case_id,
            component_verifications=verifications,
            ai_feature_detected=True,
        )

        self._run_contexts[run_id] = ctx_binding
        return ctx_binding

    def get_run_context(self, run_id: str) -> Optional[DogfoodingRunContext]:
        """Retrieve the dogfooding context binding for a run."""
        return self._run_contexts.get(run_id)

    # ─── 2. Runtime Context Verification ──────────────────────────────────

    def verify_runtime_context(
        self,
        run_id: str,
        actual_prompt: Optional[Tuple[str, int]] = None,
        actual_model: Optional[str] = None,
        actual_git_commit: Optional[str] = None,
        actual_retrieval_config: Optional[Dict[str, Any]] = None,
        actual_tool_config: Optional[Dict[str, Any]] = None,
        actual_parser_config: Optional[Dict[str, Any]] = None,
    ) -> DogfoodingRunContext:
        """
        Verifies runtime-observed values against declared context.
        Updates epistemic statuses: DECLARED -> OBSERVED on match, MISMATCH on conflict.
        Never upgrades DECLARED to OBSERVED without evidence.
        """
        ctx = self._run_contexts.get(run_id)
        if not ctx:
            raise ValueError(f"No context binding found for run '{run_id}'")

        updated_verifications = list(ctx.component_verifications)

        # Verify each component if actual values provided
        if actual_prompt is not None:
            prompt_id, prompt_ver = actual_prompt
            self._update_verification(
                updated_verifications,
                "prompt",
                declared=f"{ctx.prompt_id}:v{ctx.prompt_version}",
                observed=f"{prompt_id}:v{prompt_ver}",
            )

        if actual_model is not None:
            self._update_verification(
                updated_verifications,
                "model",
                declared=ctx.model,
                observed=actual_model,
            )

        if actual_git_commit is not None:
            self._update_verification(
                updated_verifications,
                "git_commit",
                declared=ctx.git_commit_sha or "",
                observed=actual_git_commit,
            )

        if actual_retrieval_config is not None:
            declared_hash = ctx.retrieval_configuration_hash or ""
            observed_hash = compute_config_hash(actual_retrieval_config) or ""
            self._update_verification(
                updated_verifications,
                "retrieval",
                declared=declared_hash,
                observed=observed_hash,
            )

        if actual_tool_config is not None:
            declared_hash = ctx.tool_configuration_hash or ""
            observed_hash = compute_config_hash(actual_tool_config) or ""
            self._update_verification(
                updated_verifications,
                "tools",
                declared=declared_hash,
                observed=observed_hash,
            )

        if actual_parser_config is not None:
            declared_hash = ctx.parser_configuration_hash or ""
            observed_hash = compute_config_hash(actual_parser_config) or ""
            self._update_verification(
                updated_verifications,
                "parser",
                declared=declared_hash,
                observed=observed_hash,
            )

        ctx.component_verifications = updated_verifications
        return ctx

    # ─── 3. Deterministic AI Evaluation ───────────────────────────────────

    def run_deterministic_evaluation(
        self,
        run_id: str,
        ai_output: Dict[str, Any],
        evaluation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Runs deterministic checks BEFORE AI diagnosis.
        The deterministic evaluator is authoritative over objective constraints.
        An LLM judge must not override deterministic failures.

        Returns evaluation result with:
        - passed: bool
        - deterministic_failures: list of failure descriptions
        - score: int (0-100)
        """
        ctx = self._run_contexts.get(run_id)
        failures = []
        score = 100

        # Question Generator specific rules
        if evaluation_rules and evaluation_rules.get("type") == "question_generator":
            options = ai_output.get("options", [])
            expected_count = evaluation_rules.get("expected_option_count", 4)

            # Check option count
            if len(options) != expected_count:
                failures.append(f"Expected {expected_count} options, found {len(options)}")
                score -= 25

            # Check CA indicator
            ca_opts = [
                opt for opt in options
                if (opt.get("logic") or "").strip().upper() == "CA"
            ]
            if len(ca_opts) == 0:
                failures.append("Required CA indicator absent")
                score -= 35
            elif len(ca_opts) > 1:
                failures.append("Multiple CA indicators detected")
                score -= 30

            # Duplicate detection
            seen = set()
            for opt in options:
                text = opt.get("text", "").strip().lower()
                if text in seen:
                    failures.append(f"Duplicate distractor value: {text}")
                    score -= 20
                seen.add(text)

            # Difficulty constraints
            if "difficulty" in evaluation_rules:
                expected_diff = evaluation_rules["difficulty"]
                actual_diff = ai_output.get("difficulty")
                if actual_diff and actual_diff != expected_diff:
                    failures.append(f"Difficulty mismatch: expected {expected_diff}, got {actual_diff}")
                    score -= 10

        # JSON Schema validation
        if evaluation_rules and evaluation_rules.get("type") == "json_schema":
            required_fields = evaluation_rules.get("required_fields", [])
            for field in required_fields:
                if field not in ai_output:
                    failures.append(f"Required field missing: {field}")
                    score -= 15

        # Behavioral contract checks
        if ctx and ctx.behavioral_contract_ids:
            # Record that contracts were checked
            pass

        return {
            "passed": len(failures) == 0,
            "deterministic_failures": failures,
            "score": max(0, score),
            "is_authoritative": True,  # Deterministic evaluator is authoritative
        }

    # ─── 4. Context-Aware Causal Classification ──────────────────────────

    def classify_causal_layers(
        self,
        run_id: str,
        diagnosis_id: str,
        deterministic_result: Dict[str, Any],
        evidence_refs: Optional[List[str]] = None,
        ai_diagnosis_hints: Optional[Dict[str, Any]] = None,
    ) -> CausalClassification:
        """
        Classifies failures across the Prompt Lab causal taxonomy.
        Uses evidence to support classification. Supports multiple layers.
        Never assumes PROMPT_DEFECT without evidence.
        """
        ctx = self._run_contexts.get(run_id)
        evidence = evidence_refs or []

        primary_layer = CausalLayer.UNKNOWN
        primary_epistemic = EpistemicStatus.HYPOTHESIS
        secondary_layers = []
        secondary_evidence = []
        rationale_parts = []

        det_failures = deterministic_result.get("deterministic_failures", [])

        # Analyze deterministic failures for causal classification
        has_schema_failure = any("Required field" in f for f in det_failures)
        has_constraint_failure = any(
            any(kw in f for kw in ["CA indicator", "Duplicate", "option"])
            for f in det_failures
        )
        has_difficulty_mismatch = any("Difficulty" in f for f in det_failures)

        if has_schema_failure:
            primary_layer = CausalLayer.SCHEMA_FAILURE
            primary_epistemic = EpistemicStatus.OBSERVED
            rationale_parts.append("Observed: Required output fields are missing from the structured response.")

        elif has_constraint_failure:
            # Could be prompt defect or application logic
            # Check if the model response was structurally valid
            if ai_diagnosis_hints and ai_diagnosis_hints.get("model_response_valid"):
                primary_layer = CausalLayer.PROMPT_DEFECT
                primary_epistemic = EpistemicStatus.HYPOTHESIS
                rationale_parts.append(
                    "Hypothesis: Model produced structurally valid response but constraint violations "
                    "suggest prompt instructions may not enforce uniqueness/required-option constraints."
                )
                # Application logic could also contribute
                secondary_layers.append(CausalLayer.APPLICATION_LOGIC)
                secondary_evidence.extend(evidence)
                rationale_parts.append(
                    "Hypothesis: Application validation logic may also contribute to the observed failure."
                )
            else:
                primary_layer = CausalLayer.APPLICATION_LOGIC
                primary_epistemic = EpistemicStatus.INFERRED
                rationale_parts.append(
                    "Inferred: Constraint failures detected in output; "
                    "application logic may not properly validate or transform model output."
                )

        elif has_difficulty_mismatch:
            primary_layer = CausalLayer.PROMPT_DEFECT
            primary_epistemic = EpistemicStatus.INFERRED
            rationale_parts.append("Inferred: Difficulty constraint mismatch may indicate prompt-level issue.")

        # If no deterministic failure identified a layer, check AI hints
        if primary_layer == CausalLayer.UNKNOWN and ai_diagnosis_hints:
            hint_layer = ai_diagnosis_hints.get("suspected_layer")
            if hint_layer:
                try:
                    primary_layer = CausalLayer(hint_layer)
                    primary_epistemic = EpistemicStatus.HYPOTHESIS
                    rationale_parts.append(
                        f"Hypothesis: AI diagnostician suggested {hint_layer} as potential causal layer."
                    )
                except ValueError:
                    pass

        # Check for retrieval/tool/parser failures from context verification
        if ctx:
            for v in ctx.component_verifications:
                if v.status == ContextVerificationStatus.MISMATCH:
                    if v.component == "retrieval":
                        if primary_layer == CausalLayer.UNKNOWN:
                            primary_layer = CausalLayer.RETRIEVAL_FAILURE
                            primary_epistemic = EpistemicStatus.OBSERVED
                        else:
                            secondary_layers.append(CausalLayer.RETRIEVAL_FAILURE)
                        rationale_parts.append(
                            f"Observed: Retrieval configuration mismatch detected at runtime."
                        )
                    elif v.component == "parser":
                        if primary_layer == CausalLayer.UNKNOWN:
                            primary_layer = CausalLayer.PARSER_FAILURE
                            primary_epistemic = EpistemicStatus.OBSERVED
                        else:
                            secondary_layers.append(CausalLayer.PARSER_FAILURE)
                        rationale_parts.append(
                            f"Observed: Parser configuration mismatch detected at runtime."
                        )
                    elif v.component == "tools":
                        if primary_layer == CausalLayer.UNKNOWN:
                            primary_layer = CausalLayer.TOOL_FAILURE
                            primary_epistemic = EpistemicStatus.OBSERVED
                        else:
                            secondary_layers.append(CausalLayer.TOOL_FAILURE)

        classification = CausalClassification(
            diagnosis_id=diagnosis_id,
            run_id=run_id,
            primary_layer=primary_layer,
            primary_evidence_refs=evidence,
            primary_epistemic_status=primary_epistemic,
            secondary_layers=secondary_layers,
            secondary_evidence_refs=secondary_evidence,
            rationale="\n".join(rationale_parts),
        )

        self._causal_classifications[classification.classification_id] = classification
        return classification

    # ─── 5. Prompt Improvement Proposal ──────────────────────────────────

    def propose_prompt_improvement(
        self,
        run_id: str,
        diagnosis_ids: List[str],
        evidence_ids: List[str],
        proposed_change: str,
        rationale: str,
    ) -> PromptImprovementCandidate:
        """
        Creates a PromptImprovementCandidate tied to the source context.
        This is a proposal only — no automatic production mutation.
        """
        ctx = self._run_contexts.get(run_id)
        if not ctx:
            raise ValueError(f"No context binding found for run '{run_id}'")

        candidate = PromptImprovementCandidate(
            application_id=ctx.application_id,
            feature_id=ctx.feature_id,
            source_context_id=ctx.evaluation_context_id,
            source_context_hash=ctx.context_hash,
            source_git_commit_sha=ctx.git_commit_sha,
            source_prompt_id=ctx.prompt_id,
            source_prompt_version=ctx.prompt_version,
            diagnosis_ids=diagnosis_ids,
            evidence_ids=evidence_ids,
            affected_behavioral_contract_ids=list(ctx.behavioral_contract_ids),
            proposed_prompt_change=proposed_change,
            rationale=rationale,
            status="PROPOSED",
        )

        self._prompt_candidates[candidate.candidate_id] = candidate
        return candidate

    def get_prompt_candidate(self, candidate_id: str) -> Optional[PromptImprovementCandidate]:
        return self._prompt_candidates.get(candidate_id)

    # ─── 6. Independent Retest & Regression Detection ────────────────────

    def execute_retest_comparison(
        self,
        baseline_run_id: str,
        candidate_run_id: str,
        baseline_context: EvaluationContext,
        candidate_context: EvaluationContext,
        baseline_results: Dict[str, bool],
        candidate_results: Dict[str, bool],
        baseline_contracts: Optional[Dict[str, str]] = None,
        candidate_contracts: Optional[Dict[str, str]] = None,
    ) -> RetestResult:
        """
        Compares baseline vs candidate dogfooding runs.
        Detects regressions, multi-variable changes, and contract violations.
        Original evidence is NOT reused as final verification.
        """
        # Build context comparisons
        comparisons = self._compare_contexts(baseline_context, candidate_context)
        changed_dims = [c.dimension for c in comparisons if c.status == "CHANGED"]
        is_multi_variable = len(changed_dims) > 1

        # Compute transitions
        transitions = {}
        all_checks = set(list(baseline_results.keys()) + list(candidate_results.keys()))
        for check in all_checks:
            baseline_passed = baseline_results.get(check)
            candidate_passed = candidate_results.get(check)

            if baseline_passed is None and candidate_passed is True:
                transitions[check] = RetestTransition.NEW_PASS
            elif baseline_passed is None and candidate_passed is False:
                transitions[check] = RetestTransition.NEW_FAILURE
            elif baseline_passed is False and candidate_passed is True:
                transitions[check] = RetestTransition.FIXED_FAILURE
            elif baseline_passed is True and candidate_passed is False:
                transitions[check] = RetestTransition.REGRESSION
            else:
                transitions[check] = RetestTransition.UNCHANGED

        # Compute contract evaluations
        contract_evals = {}
        if baseline_contracts and candidate_contracts:
            all_contracts = set(list(baseline_contracts.keys()) + list(candidate_contracts.keys()))
            for cid in all_contracts:
                b_status = baseline_contracts.get(cid)
                c_status = candidate_contracts.get(cid)
                if c_status == "PASS":
                    contract_evals[cid] = ContractStatus.CONTRACT_PRESERVED
                elif c_status == "FAIL":
                    contract_evals[cid] = ContractStatus.CONTRACT_VIOLATED
                else:
                    contract_evals[cid] = ContractStatus.CONTRACT_UNCERTAIN

        has_regressions = any(
            t == RetestTransition.REGRESSION for t in transitions.values()
        )

        # Ensure independent verification (different run IDs)
        is_independent = baseline_run_id != candidate_run_id

        result = RetestResult(
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_context_id=baseline_context.context_id,
            candidate_context_id=candidate_context.context_id,
            transitions=transitions,
            contract_evaluations=contract_evals,
            comparisons=comparisons,
            changed_dimensions=changed_dims,
            is_multi_variable_change=is_multi_variable,
            is_independently_verified=is_independent,
            has_regressions=has_regressions,
        )

        self._retest_results[result.retest_id] = result
        return result

    def get_retest_result(self, retest_id: str) -> Optional[RetestResult]:
        return self._retest_results.get(retest_id)

    # ─── 7. Governance Integration Helpers ────────────────────────────────

    def validate_authorization_binding(
        self,
        authorization_version: Optional[str],
        authorization_commit: Optional[str],
        target_version: str,
        target_commit: str,
    ) -> Dict[str, Any]:
        """
        Validates that authorization matches the exact target.
        Authorization for Prompt v18 must never authorize Prompt v19.
        Authorization for Commit abc123 must never authorize Commit def456.
        """
        version_match = authorization_version == target_version
        commit_match = authorization_commit == target_commit
        is_valid = version_match and commit_match

        blockers = []
        if not version_match:
            blockers.append(
                f"Version mismatch: authorized='{authorization_version}', target='{target_version}'"
            )
        if not commit_match:
            blockers.append(
                f"Commit mismatch: authorized='{authorization_commit}', target='{target_commit}'"
            )

        return {
            "is_valid": is_valid,
            "version_match": version_match,
            "commit_match": commit_match,
            "blockers": blockers,
        }

    # ─── Private Helpers ─────────────────────────────────────────────────

    def _build_verifications_from_provenance(
        self, provenance: List[ContextProvenance]
    ) -> List[ComponentVerification]:
        """Build component verifications from context provenance records."""
        verifications = []
        for p in provenance:
            status = ContextVerificationStatus.UNAVAILABLE
            if p.epistemic_status == EpistemicStatus.OBSERVED:
                status = ContextVerificationStatus.VERIFIED
            verifications.append(
                ComponentVerification(
                    component=p.component,
                    status=status,
                    epistemic_status=p.epistemic_status,
                    declared_value=p.source_version,
                )
            )
        return verifications

    def _update_verification(
        self,
        verifications: List[ComponentVerification],
        component: str,
        declared: str,
        observed: str,
    ) -> None:
        """Update a component verification with observed runtime values."""
        for v in verifications:
            if v.component == component:
                v.observed_value = observed
                if declared == observed:
                    v.status = ContextVerificationStatus.VERIFIED
                    v.epistemic_status = EpistemicStatus.OBSERVED
                else:
                    v.status = ContextVerificationStatus.MISMATCH
                    v.mismatch_detail = (
                        f"Declared: {declared}, Observed: {observed}"
                    )
                return

        # Component not in provenance, add new verification
        match = declared == observed
        verifications.append(
            ComponentVerification(
                component=component,
                status=ContextVerificationStatus.VERIFIED if match else ContextVerificationStatus.MISMATCH,
                epistemic_status=EpistemicStatus.OBSERVED if match else EpistemicStatus.DECLARED,
                declared_value=declared,
                observed_value=observed,
                mismatch_detail=None if match else f"Declared: {declared}, Observed: {observed}",
            )
        )

    def _compare_contexts(
        self,
        baseline: EvaluationContext,
        candidate: EvaluationContext,
    ) -> List[RetestComparison]:
        """Build explicit dimension-by-dimension comparison between two contexts."""
        dims = [
            ("prompt_version", str(baseline.prompt_version), str(candidate.prompt_version)),
            ("model", baseline.model, candidate.model),
            ("model_version", baseline.model_version or "", candidate.model_version or ""),
            ("git_commit_sha", baseline.git_commit_sha or "", candidate.git_commit_sha or ""),
            ("retrieval", compute_config_hash(baseline.retrieval_configuration) or "",
             compute_config_hash(candidate.retrieval_configuration) or ""),
            ("tools", compute_config_hash(baseline.tool_configuration) or "",
             compute_config_hash(candidate.tool_configuration) or ""),
            ("parser", compute_config_hash(baseline.parser_configuration) or "",
             compute_config_hash(candidate.parser_configuration) or ""),
            ("behavioral_contracts",
             json.dumps(sorted(baseline.behavioral_contract_ids)),
             json.dumps(sorted(candidate.behavioral_contract_ids))),
        ]

        comparisons = []
        for dim_name, b_val, c_val in dims:
            status = "SAME" if b_val == c_val else "CHANGED"
            comparisons.append(
                RetestComparison(
                    dimension=dim_name,
                    baseline_value=b_val,
                    candidate_value=c_val,
                    status=status,
                )
            )
        return comparisons
