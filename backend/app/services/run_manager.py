import asyncio
from datetime import datetime, timezone
import uuid

from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.metric import Metric
from backend.app.models.enums import RunStatus, RunnerType, PredictionEvaluationStatus, ExecutionSource
from backend.app.repositories.base import (
    RunRepositoryInterface,
    TargetRepositoryInterface,
    TestCaseRepositoryInterface,
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    MetricRepositoryInterface,
)
from backend.app.execution.base_runner import BaseTestRunner
from backend.app.core.exceptions import NotFoundException

class RunManager:
    """
    Coordinates the test run lifecycle:
    Submission -> Dispatch -> Execution Engine (Playwright / Mock) -> Evidence & Telemetry Aggregation -> Persistence.
    """
    def __init__(
        self,
        run_repo: RunRepositoryInterface,
        target_repo: TargetRepositoryInterface,
        test_case_repo: TestCaseRepositoryInterface,
        evidence_repo: EvidenceRepositoryInterface,
        failure_repo: FailureRepositoryInterface,
        metric_repo: MetricRepositoryInterface,
        runner: BaseTestRunner | None = None,
        runners: dict[RunnerType, BaseTestRunner] | None = None,
    ):
        self.run_repo = run_repo
        self.target_repo = target_repo
        self.test_case_repo = test_case_repo
        self.evidence_repo = evidence_repo
        self.failure_repo = failure_repo
        self.metric_repo = metric_repo
        self.runners: dict[RunnerType, BaseTestRunner] = runners or {}
        if runner:
            self.runners[RunnerType.MOCK] = runner
            if RunnerType.PLAYWRIGHT not in self.runners:
                self.runners[RunnerType.PLAYWRIGHT] = runner

    def get_runner(self, runner_type: RunnerType | str | None) -> BaseTestRunner:
        if isinstance(runner_type, str):
            try:
                runner_type = RunnerType(runner_type)
            except ValueError:
                runner_type = RunnerType.MOCK
        
        target_type = runner_type or RunnerType.MOCK
        if target_type in self.runners:
            return self.runners[target_type]
        if RunnerType.MOCK in self.runners:
            return self.runners[RunnerType.MOCK]
        if self.runners:
            return next(iter(self.runners.values()))
        raise RuntimeError("No test runners registered in RunManager")

    async def initiate_run(self, payload: TestRunCreate) -> TestRun:
        target = self.target_repo.get_target(payload.application_id)
        if not target:
            # Look up or create target if demo
            targets = self.target_repo.list_targets()
            if targets:
                target = targets[0]
            else:
                raise NotFoundException(f"Application target '{payload.application_id}' not found")

        runner_type = payload.runner_type or RunnerType.MOCK

        # Determine explicit immutable execution provenance from runner configuration
        if payload.execution_source and payload.execution_source != ExecutionSource.UNKNOWN:
            exec_source = payload.execution_source
        elif runner_type == RunnerType.PLAYWRIGHT:
            exec_source = ExecutionSource.REAL_PLAYWRIGHT
        elif runner_type == RunnerType.AI_AGENT:
            exec_source = ExecutionSource.REAL_AI_AGENT
        elif runner_type == RunnerType.MOCK:
            exec_source = ExecutionSource.SYNTHETIC_MOCK
        else:
            exec_source = ExecutionSource.UNKNOWN

        run = TestRun(
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            application_id=target.target_id,
            application_version=payload.application_version or target.version,
            test_mode=payload.test_mode,
            runner_type=runner_type,
            execution_source=exec_source,
            test_case_id=payload.test_case_id,
            status=RunStatus.QUEUED,
            environment_id=payload.environment_id,
            natural_language_goal=payload.natural_language_goal,
            max_agent_steps=payload.max_agent_steps,
            campaign_id=payload.campaign_id,
            campaign_type=payload.campaign_type,
            started_at=datetime.now(timezone.utc).isoformat(),
            logs=[f"[INIT] Created test run for target: {target.name} ({target.target_id}) in mode {payload.test_mode.value} using {runner_type.value} engine (source: {exec_source.value})"],
        )

        self.run_repo.create_run(run)

        # Dispatch to the chosen executor
        executor = self.get_runner(runner_type)
        executed_run = await executor.execute(run, target, payload)

        # Continuous prediction outcome evaluation
        if executed_run.test_case_id and hasattr(self.run_repo, "get_pending_predictions_for_test_case"):
            try:
                pending_list = self.run_repo.get_pending_predictions_for_test_case(executed_run.test_case_id)
                if pending_list:
                    status_val = executed_run.status.value if hasattr(executed_run.status, "value") else str(executed_run.status)
                    is_failed = status_val in ("FAILED", "ERROR")
                    actual_outcome = 1 if is_failed else 0
                    now_iso = datetime.now(timezone.utc).isoformat()
                    for p in pending_list:
                        if p.feature_run_id != executed_run.run_id:
                            p.target_run_id = executed_run.run_id
                            p.actual_outcome = actual_outcome
                            p.is_correct = (p.prediction_class == actual_outcome)
                            p.evaluation_status = PredictionEvaluationStatus.EVALUATED
                            p.evaluated_at = now_iso
                            self.run_repo.update_prediction_record(p)
            except Exception:
                pass

        return executed_run

    def get_run(self, run_id: str) -> TestRun:
        run = self.run_repo.get_run(run_id)
        if not run:
            raise NotFoundException(f"Test run with ID '{run_id}' not found")
        return run

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        application_id: str | None = None,
        test_mode: str | None = None,
        status: str | None = None,
    ) -> list[TestRun]:
        return self.run_repo.list_runs(
            limit=limit,
            offset=offset,
            application_id=application_id,
            test_mode=test_mode,
            status=status,
        )

    def count_runs(
        self,
        application_id: str | None = None,
        test_mode: str | None = None,
        status: str | None = None,
    ) -> int:
        return self.run_repo.count_runs(
            application_id=application_id,
            test_mode=test_mode,
            status=status,
        )

    def get_run_evidence(self, run_id: str) -> list[Evidence]:
        self.get_run(run_id) # ensure exists
        return self.evidence_repo.get_evidence_by_run(run_id)

    def get_evidence_detail(self, evidence_id: str) -> Evidence:
        evidence = self.evidence_repo.get_evidence(evidence_id)
        if not evidence:
            raise NotFoundException(f"Evidence record '{evidence_id}' not found")
        return evidence

    def get_run_failures(self, run_id: str) -> list[Failure]:
        self.get_run(run_id) # ensure exists
        return self.failure_repo.get_failures_by_run(run_id)

    def get_run_metrics(self, run_id: str) -> list[Metric]:
        self.get_run(run_id) # ensure exists
        return self.metric_repo.get_metrics_by_run(run_id)
