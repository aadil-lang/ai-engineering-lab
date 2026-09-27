import uuid
import time
import json
import hashlib
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    EvaluationSuite,
    EvaluationSuiteVersion,
    EvaluationCase,
    EvaluationRun,
    CaseEvaluationResult,
    AIExecutionRecord,
    EvaluationStatus,
    EvaluationStrategy,
    SeverityLevel,
    PromptDiagnosis,
    PromptComparisonResult,
    CaseTransitionRecord,
    CaseTransition,
    EvaluationSnapshot,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.prompt_service import PromptService, redact_secrets
from backend.app.prompt_lab.evaluator_service import CompositeEvaluator
from backend.app.prompt_lab.diagnosis_service import PromptDiagnosisService
from backend.app.prompt_lab.errors import (
    EvaluationSuiteNotFoundError,
    EvaluationCaseNotFoundError,
    EvaluationRunNotFoundError,
    PromptLabError,
)


class EvaluationService:
    """
    Orchestrates prompt evaluations, reproducible execution capture,
    multi-layer diagnosis, prompt comparisons, and regression detection.
    """

    def __init__(
        self,
        repo: Optional[PromptLabRepository] = None,
        prompt_service: Optional[PromptService] = None,
        diagnosis_service: Optional[PromptDiagnosisService] = None,
    ):
        self.repo = repo or PromptLabRepository()
        self.prompt_service = prompt_service or PromptService(self.repo)
        self.diagnosis_service = diagnosis_service or PromptDiagnosisService()
        self.evaluator = CompositeEvaluator()

    # 1. Suite Management
    def create_suite(self, suite_id: str, name: str, description: str = "") -> EvaluationSuite:
        s = EvaluationSuite(suite_id=suite_id, name=name, description=description)
        return self.repo.save_suite(s)

    def get_suite(self, suite_id: str) -> EvaluationSuite:
        s = self.repo.get_suite(suite_id)
        if not s:
            raise EvaluationSuiteNotFoundError(f"Suite '{suite_id}' does not exist.")
        return s

    def list_suites(self) -> List[EvaluationSuite]:
        return self.repo.list_suites()

    def create_suite_version(
        self,
        suite_id: str,
        cases: List[EvaluationCase],
        description: str = "",
        is_frozen: bool = False,
    ) -> EvaluationSuiteVersion:
        self.get_suite(suite_id)
        existing = [self.repo.get_suite_version(suite_id, v) for v in range(1, 100)]
        existing = [v for v in existing if v is not None]
        next_ver = (max(v.version for v in existing) + 1) if existing else 1

        sv = EvaluationSuiteVersion(
            suite_id=suite_id,
            version=next_ver,
            description=description,
            cases=cases,
            is_frozen=is_frozen,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.repo.save_suite_version(sv)

    def get_suite_version(self, suite_id: str, version: int) -> EvaluationSuiteVersion:
        sv = self.repo.get_suite_version(suite_id, version)
        if not sv:
            raise EvaluationSuiteNotFoundError(f"Suite version {suite_id}:v{version} does not exist.")
        return sv

    def freeze_suite_version(self, suite_id: str, version: int):
        self.repo.freeze_suite_version(suite_id, version)

    # 2. Evaluation Execution
    def execute_evaluation(
        self,
        prompt_id: str,
        prompt_version: int,
        suite_id: str,
        suite_version: int,
        model: str = "mock-agent-v1",
        generation_parameters: Optional[Dict[str, Any]] = None,
        model_runner: Optional[Callable[[str, EvaluationCase], str]] = None,
        application_version: Optional[str] = None,
        git_commit_sha: Optional[str] = None,
    ) -> EvaluationRun:
        pv = self.prompt_service.get_prompt_version(prompt_id, prompt_version)
        sv = self.get_suite_version(suite_id, suite_version)

        # Mark prompt evaluated and suite frozen for immutability
        self.repo.mark_prompt_version_evaluated(prompt_id, prompt_version)
        if not sv.is_frozen:
            self.repo.freeze_suite_version(suite_id, suite_version)

        run_id = f"eval_run_{uuid.uuid4().hex[:12]}"
        gen_params = generation_parameters or {"temperature": 0.0, "max_tokens": 1024}
        started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.time()

        case_results: List[CaseEvaluationResult] = []
        diagnoses: List[PromptDiagnosis] = []

        passed_count = 0
        failed_count = 0
        partial_count = 0
        unknown_count = 0
        abstained_count = 0

        for case in sv.cases:
            # 1. Render prompt
            rendered_prompt, rendered_hash = self.prompt_service.render_prompt(pv, case.input)
            input_hash = hashlib.sha256(json.dumps(case.input, sort_keys=True).encode("utf-8")).hexdigest()

            # 2. Model execution
            t_exec_start = time.time()
            if model_runner:
                raw_output = model_runner(rendered_prompt, case)
            else:
                raw_output = self._default_mock_runner(rendered_prompt, pv, case)
            exec_duration = int((time.time() - t_exec_start) * 1000)

            # Scrub secrets and ensure no chain of thought
            raw_output = redact_secrets(raw_output)
            output_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()

            exec_record = AIExecutionRecord(
                execution_id=f"exec_{uuid.uuid4().hex[:10]}",
                evaluation_run_id=run_id,
                evaluation_case_id=case.case_id,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                model=model,
                model_version="1.0",
                generation_parameters=gen_params,
                input_hash=input_hash,
                rendered_prompt_hash=rendered_hash,
                output_hash=output_hash,
                rendered_prompt=rendered_prompt,
                raw_output=raw_output,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=exec_duration,
                tool_usage=[],
                retrieval_usage=[{"source_count": len(case.sources)}] if case.sources else [],
                application_version=application_version,
                git_commit_sha=git_commit_sha,
            )

            # 3. Composite Evaluation
            status, ev_results, score = self.evaluator.evaluate_case(
                case=case,
                raw_output=raw_output,
                output_schema=pv.output_schema,
            )

            if status == EvaluationStatus.PASS:
                passed_count += 1
            elif status == EvaluationStatus.FAIL:
                failed_count += 1
            elif status == EvaluationStatus.PARTIAL:
                partial_count += 1
            elif status == EvaluationStatus.UNKNOWN:
                unknown_count += 1
            elif status == EvaluationStatus.ABSTAINED:
                abstained_count += 1

            # 4. Failure Diagnosis if not clean pass
            failure_causes = []
            if status != EvaluationStatus.PASS:
                diag = self.diagnosis_service.diagnose_failure(
                    evaluation_run_id=run_id,
                    case=case,
                    evaluator_results=ev_results,
                    execution=exec_record,
                )
                self.repo.save_diagnosis(diag)
                diagnoses.append(diag)
                failure_causes.append(diag.primary_cause)

            case_res = CaseEvaluationResult(
                case_id=case.case_id,
                category=case.category,
                severity=case.severity,
                overall_status=status,
                evaluator_results=ev_results,
                failure_causes=failure_causes,
                evidence_ids=[exec_record.execution_id],
                execution=exec_record,
                confidence=score,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            case_results.append(case_res)

        total_cases = len(sv.cases)
        pass_rate = round(passed_count / total_cases, 4) if total_cases > 0 else 0.0
        duration_total = int((time.time() - t0) * 1000)

        run = EvaluationRun(
            evaluation_run_id=run_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            suite_id=suite_id,
            suite_version=suite_version,
            model=model,
            generation_parameters=gen_params,
            status="COMPLETED",
            total_cases=total_cases,
            passed_cases=passed_count,
            failed_cases=failed_count,
            partial_cases=partial_count,
            unknown_cases=unknown_count,
            abstained_cases=abstained_count,
            pass_rate=pass_rate,
            case_results=case_results,
            diagnoses=diagnoses,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=duration_total,
        )
        self.repo.save_run(run)

        # 5. Create immutable Evaluation Snapshot
        self.create_evaluation_snapshot(run)

        return run

    def create_evaluation_snapshot(self, run: EvaluationRun) -> EvaluationSnapshot:
        snap_id = f"eval_snap_{run.prompt_id}_v{run.prompt_version}_{run.suite_id}_v{run.suite_version}"
        content_dict = {
            "snapshot_id": snap_id,
            "protocol_version": "PromptEvaluationProtocol v1.0",
            "prompt_id": run.prompt_id,
            "prompt_version": run.prompt_version,
            "suite_id": run.suite_id,
            "suite_version": run.suite_version,
            "model": run.model,
            "model_parameters": run.generation_parameters,
            "dataset_provenance": {
                "suite_id": run.suite_id,
                "suite_version": run.suite_version,
                "total_cases": run.total_cases,
            },
            "evaluation_run_id": run.evaluation_run_id,
            "total_cases": run.total_cases,
            "passed_cases": run.passed_cases,
            "failed_cases": run.failed_cases,
            "pass_rate": run.pass_rate,
            "evaluator_versions": {
                "CompositeEvaluator": "1.0",
                "JSONSchemaEvaluator": "1.0",
                "RuleBasedEvaluator": "1.0",
                "ExactMatchEvaluator": "1.0",
                "GroundingEvaluator": "1.0",
                "SemanticJudgeEvaluator": "1.0",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sha_hash = hashlib.sha256(json.dumps(content_dict, sort_keys=True).encode("utf-8")).hexdigest()

        snapshot = EvaluationSnapshot(
            snapshot_id=snap_id,
            protocol_version="PromptEvaluationProtocol v1.0",
            prompt_id=run.prompt_id,
            prompt_version=run.prompt_version,
            suite_id=run.suite_id,
            suite_version=run.suite_version,
            model=run.model,
            model_parameters=run.generation_parameters,
            dataset_provenance=content_dict["dataset_provenance"],
            evaluation_run_id=run.evaluation_run_id,
            total_cases=run.total_cases,
            passed_cases=run.passed_cases,
            failed_cases=run.failed_cases,
            pass_rate=run.pass_rate,
            evaluator_versions=content_dict["evaluator_versions"],
            sha256_hash=sha_hash,
            timestamp=content_dict["timestamp"],
        )
        return self.repo.save_snapshot(snapshot)

    # 3. Prompt Version Comparison & Regression Detection
    def compare_prompt_versions(
        self,
        prompt_id: str,
        v1_version: int,
        v2_version: int,
        suite_id: str,
        suite_version: int,
    ) -> PromptComparisonResult:
        runs_v1 = [
            r for r in self.repo.list_runs_for_prompt(prompt_id, v1_version)
            if r.suite_id == suite_id and r.suite_version == suite_version
        ]
        runs_v2 = [
            r for r in self.repo.list_runs_for_prompt(prompt_id, v2_version)
            if r.suite_id == suite_id and r.suite_version == suite_version
        ]

        if not runs_v1:
            raise EvaluationRunNotFoundError(f"No completed evaluation run found for {prompt_id}:v{v1_version} on suite {suite_id}:v{suite_version}.")
        if not runs_v2:
            raise EvaluationRunNotFoundError(f"No completed evaluation run found for {prompt_id}:v{v2_version} on suite {suite_id}:v{suite_version}.")

        run_v1 = runs_v1[0]
        run_v2 = runs_v2[0]

        map_v1 = {r.case_id: r for r in run_v1.case_results}
        map_v2 = {r.case_id: r for r in run_v2.case_results}

        all_case_ids = list(dict.fromkeys(list(map_v1.keys()) + list(map_v2.keys())))

        transitions: List[CaseTransitionRecord] = []
        critical_regressions: List[CaseTransitionRecord] = []

        regressions_count = 0
        fixed_count = 0
        unchanged_count = 0
        new_passes_count = 0
        new_failures_count = 0

        for case_id in all_case_ids:
            r1 = map_v1.get(case_id)
            r2 = map_v2.get(case_id)

            s1 = r1.overall_status if r1 else EvaluationStatus.UNKNOWN
            s2 = r2.overall_status if r2 else EvaluationStatus.UNKNOWN
            cat = (r2 or r1).category
            sev = (r2 or r1).severity

            if s1 == EvaluationStatus.PASS and s2 == EvaluationStatus.PASS:
                trans = CaseTransition.UNCHANGED
                unchanged_count += 1
            elif s1 == EvaluationStatus.FAIL and s2 == EvaluationStatus.FAIL:
                trans = CaseTransition.UNCHANGED
                unchanged_count += 1
            elif s1 in {EvaluationStatus.FAIL, EvaluationStatus.PARTIAL, EvaluationStatus.UNKNOWN} and s2 == EvaluationStatus.PASS:
                trans = CaseTransition.FIXED_FAILURE if s1 == EvaluationStatus.FAIL else CaseTransition.NEW_PASS
                if trans == CaseTransition.FIXED_FAILURE:
                    fixed_count += 1
                else:
                    new_passes_count += 1
            elif s1 == EvaluationStatus.PASS and s2 in {EvaluationStatus.FAIL, EvaluationStatus.PARTIAL, EvaluationStatus.UNKNOWN}:
                trans = CaseTransition.REGRESSION
                regressions_count += 1
            elif s1 in {EvaluationStatus.UNKNOWN, EvaluationStatus.ABSTAINED} and s2 == EvaluationStatus.FAIL:
                trans = CaseTransition.NEW_FAILURE
                new_failures_count += 1
            else:
                trans = CaseTransition.UNCHANGED
                unchanged_count += 1

            record = CaseTransitionRecord(
                case_id=case_id,
                category=cat,
                severity=sev,
                status_v1=s1,
                status_v2=s2,
                transition=trans,
                rationale_diff=f"v1: {s1.value} -> v2: {s2.value}",
            )
            transitions.append(record)

            if trans == CaseTransition.REGRESSION and sev in {SeverityLevel.CRITICAL, SeverityLevel.HIGH}:
                critical_regressions.append(record)

        # Multi-dimensional breakdown
        det_v1 = sum(1 for r in run_v1.case_results if any(e.strategy in {EvaluationStrategy.JSON_SCHEMA, EvaluationStrategy.RULE_BASED} and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v1.total_cases or 1)
        det_v2 = sum(1 for r in run_v2.case_results if any(e.strategy in {EvaluationStrategy.JSON_SCHEMA, EvaluationStrategy.RULE_BASED} and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v2.total_cases or 1)

        ground_v1 = sum(1 for r in run_v1.case_results if any(e.strategy == EvaluationStrategy.GROUNDING and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v1.total_cases or 1)
        ground_v2 = sum(1 for r in run_v2.case_results if any(e.strategy == EvaluationStrategy.GROUNDING and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v2.total_cases or 1)

        sem_v1 = sum(1 for r in run_v1.case_results if any(e.strategy == EvaluationStrategy.SEMANTIC_JUDGE and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v1.total_cases or 1)
        sem_v2 = sum(1 for r in run_v2.case_results if any(e.strategy == EvaluationStrategy.SEMANTIC_JUDGE and e.status == EvaluationStatus.PASS for e in r.evaluator_results)) / (run_v2.total_cases or 1)

        return PromptComparisonResult(
            prompt_id=prompt_id,
            v1_version=v1_version,
            v2_version=v2_version,
            suite_id=suite_id,
            suite_version=suite_version,
            v1_run_id=run_v1.evaluation_run_id,
            v2_run_id=run_v2.evaluation_run_id,
            v1_pass_rate=run_v1.pass_rate,
            v2_pass_rate=run_v2.pass_rate,
            pass_rate_delta=round(run_v2.pass_rate - run_v1.pass_rate, 4),
            total_cases=len(all_case_ids),
            regressions_count=regressions_count,
            fixed_failures_count=fixed_count,
            unchanged_count=unchanged_count,
            new_passes_count=new_passes_count,
            new_failures_count=new_failures_count,
            critical_regressions=critical_regressions,
            transitions=transitions,
            deterministic_pass_rates={"v1": round(det_v1, 4), "v2": round(det_v2, 4)},
            grounding_pass_rates={"v1": round(ground_v1, 4), "v2": round(ground_v2, 4)},
            semantic_pass_rates={"v1": round(sem_v1, 4), "v2": round(sem_v2, 4)},
        )

    # Helper: default mock runner
    def _default_mock_runner(self, rendered_prompt: str, pv, case: EvaluationCase) -> str:
        # If expected output is provided, return clean output
        if case.expected_output is not None:
            if isinstance(case.expected_output, dict):
                return json.dumps(case.expected_output)
            return str(case.expected_output)

        # If schema is required, produce conforming JSON
        if pv.output_schema:
            res: Dict[str, Any] = {}
            for req in pv.output_schema.get("required", []):
                res[req] = f"sample_{req}"
            return json.dumps(res)

        # Default text
        return f"Response addressing: {case.expected_behavior}."
