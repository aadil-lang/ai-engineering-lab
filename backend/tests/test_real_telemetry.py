import pytest
import uuid
import os
from datetime import datetime, timezone

from backend.app.models.enums import (
    RunnerType,
    ExecutionSource,
    RunStatus,
    ActionType,
    ActionStatus,
    FailureCategory,
    Severity,
    PopulationType,
    TargetType,
)
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget
from backend.app.models.failure import Failure
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import PopulationSeparator
from backend.app.execution.playwright_runner import PlaywrightTestRunner


def test_explicit_real_execution_provenance():
    """Verifies provenance is strictly determined from runner configuration and never heuristically inferred."""
    # 1. Real Playwright Runner
    run_pw = TestRun(
        run_id="run_pw_test",
        application_id="target_tgt_demo_shop",  # Even with demo target, runner config establishes REAL_PLAYWRIGHT
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_pw) == ExecutionSource.REAL_PLAYWRIGHT

    # 2. Real AI Agent Runner
    run_ai = TestRun(
        run_id="run_ai_test",
        application_id="target_tgt_demo_shop",
        runner_type=RunnerType.AI_AGENT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_ai) == ExecutionSource.REAL_AI_AGENT

    # 3. Explicit persisted provenance is strictly honored
    run_explicit = TestRun(
        run_id="run_exp_test",
        application_id="real_prod_app",
        execution_source=ExecutionSource.DEMO_HARNESS,
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_explicit) == ExecutionSource.DEMO_HARNESS

    # 4. Unknown provenance if not established
    class MockUnconfiguredRun:
        runner_type = "UNRECOGNIZED_ENGINE"
        execution_source = ExecutionSource.UNKNOWN
        application_id = "real_app"
        test_case_id = "tc_login"

    assert ReliabilityFeatureExtractor.classify_execution_source(MockUnconfiguredRun()) == ExecutionSource.UNKNOWN


def test_sqlite_persistence_required_provenance_fields(tmp_path):
    """Verifies all required Slice 6.5 fields persist and round-trip correctly through SQLite."""
    db_file = str(tmp_path / "test_provenance.db")
    repo = SQLiteRepository(db_path=db_file)

    target = ApplicationTarget(
        target_id="target_real_app_1",
        name="Production Portal",
        target_type=TargetType.WEB_APPLICATION,
        base_url="https://app.example.com",
        environment="production",
        version="2.4.0",
    )
    repo.create_target(target)

    run = TestRun(
        run_id="run_real_telemetry_101",
        application_id="target_real_app_1",
        application_version="2.4.0",
        runner_type=RunnerType.PLAYWRIGHT,
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        test_case_id="tc_auth_flow",
        status=RunStatus.PASSED,
        started_at="2026-09-24T20:00:00Z",
        finished_at="2026-09-24T20:00:05Z",
        duration_ms=5120,
        environment_id="env_production",
        feature_vector_version="v1.0-temporal",
        metrics_summary={
            "run_duration_ms": 5120.0,
            "total_steps": 5.0,
            "successful_steps": 5.0,
            "failed_steps": 0.0,
            "retries": 0.0,
            "timeout": 0.0,
            "final_status": 1.0,
            "request_count": 14.0,
            "response_count": 14.0,
            "http_4xx_count": 0.0,
            "http_5xx_count": 0.0,
            "failed_requests": 0.0,
            "network_exceptions": 0.0,
            "console_errors_count": 0.0,
            "console_warnings_count": 1.0,
        },
    )
    repo.create_run(run)

    fetched = repo.get_run("run_real_telemetry_101")
    assert fetched is not None
    assert fetched.run_id == "run_real_telemetry_101"
    assert fetched.application_id == "target_real_app_1"
    assert fetched.test_case_id == "tc_auth_flow"
    assert fetched.execution_source == ExecutionSource.REAL_PLAYWRIGHT
    assert fetched.runner_type == RunnerType.PLAYWRIGHT
    assert fetched.started_at == "2026-09-24T20:00:00Z"
    assert fetched.finished_at == "2026-09-24T20:00:05Z"
    assert fetched.environment_id == "env_production"
    assert fetched.feature_vector_version == "v1.0-temporal"
    assert fetched.metrics_summary["request_count"] == 14.0
    assert fetched.metrics_summary["console_warnings_count"] == 1.0


def test_sqlite_failure_provenance_and_selector_fields(tmp_path):
    """Verifies Failure records store failed_action and selector for precise attribution."""
    db_file = str(tmp_path / "test_failures.db")
    repo = SQLiteRepository(db_path=db_file)

    failure = Failure(
        failure_id="fail_pw_step4",
        run_id="run_real_telemetry_102",
        action_id="act_checkout_btn",
        category=FailureCategory.CLICK_FAILED,
        severity=Severity.HIGH,
        title="Element intercepted",
        message="Button '#checkout-submit' was obscured by overlay",
        stack_trace="PlaywrightError: target element intercepted at ...",
        suggested_remediation="Verify overlay dismissal before click.",
        failed_action="CLICK",
        selector="#checkout-submit",
    )
    repo.save_failure(failure)

    fetched = repo.get_failure("fail_pw_step4")
    assert fetched is not None
    assert fetched.failed_action == "CLICK"
    assert fetched.selector == "#checkout-submit"
    assert fetched.category == FailureCategory.CLICK_FAILED

    failures_for_run = repo.get_failures_by_run("run_real_telemetry_102")
    assert len(failures_for_run) == 1
    assert failures_for_run[0].failed_action == "CLICK"
    assert failures_for_run[0].selector == "#checkout-submit"


def test_playwright_telemetry_pipeline_compilation():
    """Verifies PlaywrightTestRunner telemetry compilation captures all mandatory telemetry dimensions."""
    class DummyRunRepo:
        def update_run(self, run): pass
    class DummyEviRepo:
        def save_evidence(self, e): pass
    class DummyFailRepo:
        def save_failure(self, f): pass
    class DummyMetRepo:
        def save_metric(self, m): pass

    runner = PlaywrightTestRunner(
        run_repo=DummyRunRepo(),
        evidence_repo=DummyEviRepo(),
        failure_repo=DummyFailRepo(),
        metric_repo=DummyMetRepo(),
    )

    run = TestRun(
        run_id="run_comp_test",
        application_id="app_test",
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )

    captured_network = [
        {"event": "request", "url": "https://example.com/api/user", "method": "GET"},
        {"event": "response", "url": "https://example.com/api/user", "status": 200, "ok": True},
        {"event": "request", "url": "https://example.com/api/missing", "method": "GET"},
        {"event": "response", "url": "https://example.com/api/missing", "status": 404, "ok": False},
        {"event": "request", "url": "https://example.com/api/crash", "method": "POST"},
        {"event": "response", "url": "https://example.com/api/crash", "status": 500, "ok": False},
        {"event": "request_failed", "url": "https://example.com/api/dropped", "failure": "net::ERR_CONNECTION_RESET"},
    ]

    captured_console = [
        {"type": "error", "text": "Uncaught TypeError: Cannot read property 'map' of undefined"},
        {"type": "warn", "text": "Deprecation warning: component will unmount soon"},
        {"type": "info", "text": "App rendered in 45ms"},
    ]

    runner._compile_telemetry(
        run=run,
        total_duration=3200,
        captured_network_events=captured_network,
        captured_console_logs=captured_console,
        page_url="https://example.com/app",
        is_timeout=False,
    )

    summary = run.metrics_summary
    # Execution
    assert summary["run_duration_ms"] == 3200.0
    assert summary["retries"] == 0.0
    assert summary["timeout"] == 0.0
    assert summary["final_status"] == 1.0

    # Network
    assert summary["request_count"] == 3.0
    assert summary["response_count"] == 3.0
    assert summary["http_4xx_count"] == 1.0
    assert summary["http_5xx_count"] == 1.0
    assert summary["failed_requests"] == 2.0
    assert summary["network_exceptions"] == 1.0

    # Console
    assert summary["console_errors_count"] == 1.0
    assert summary["console_warnings_count"] == 1.0


def test_population_separation_with_real_telemetry():
    """Verifies that adding genuine REAL_PLAYWRIGHT records cleanly separates into real populations."""
    # Build 10 mock/demo records
    mock_records = [
        ReliabilityFeatureExtractor.extract_record_from_run(
            TestRun(
                run_id=f"run_mock_{i}",
                application_id="app_mock",
                runner_type=RunnerType.MOCK,
                execution_source=ExecutionSource.SYNTHETIC_MOCK,
                status=RunStatus.PASSED,
                started_at=f"2026-09-24T10:{i:02d}:00Z",
            ),
            evidence_items=[],
            failures=[],
        )
        for i in range(10)
    ]

    # Build 5 genuine real playwright records
    real_records = [
        ReliabilityFeatureExtractor.extract_record_from_run(
            TestRun(
                run_id=f"run_real_{i}",
                application_id="app_production",
                runner_type=RunnerType.PLAYWRIGHT,
                execution_source=ExecutionSource.REAL_PLAYWRIGHT,
                status=RunStatus.PASSED if i % 2 == 0 else RunStatus.FAILED,
                started_at=f"2026-09-24T12:{i:02d}:00Z",
            ),
            evidence_items=[],
            failures=[],
        )
        for i in range(5)
    ]

    all_records = mock_records + real_records

    # Population A: ALL_HISTORICAL contains all 15
    pop_a = PopulationSeparator.filter_records_by_population(all_records, PopulationType.ALL_HISTORICAL)
    assert len(pop_a) == 15

    # Population B: REAL_EXECUTIONS_ONLY contains strictly the 5 real records
    pop_b = PopulationSeparator.filter_records_by_population(all_records, PopulationType.REAL_EXECUTIONS_ONLY)
    assert len(pop_b) == 5
    assert all(r.execution_source in (ExecutionSource.REAL_PLAYWRIGHT, ExecutionSource.REAL_AI_AGENT) for r in pop_b)

    # Population C: REAL_PLAYWRIGHT_ONLY contains strictly the 5 real playwright records
    pop_c = PopulationSeparator.filter_records_by_population(all_records, PopulationType.REAL_PLAYWRIGHT_ONLY)
    assert len(pop_c) == 5
    assert all(r.execution_source == ExecutionSource.REAL_PLAYWRIGHT for r in pop_c)

    # Population D: REAL_AI_AGENT_ONLY has 0
    pop_d = PopulationSeparator.filter_records_by_population(all_records, PopulationType.REAL_AI_AGENT_ONLY)
    assert len(pop_d) == 0

    # Population E: CONTROLLED_AND_DEMO contains strictly the 10 mock records
    pop_e = PopulationSeparator.filter_records_by_population(all_records, PopulationType.CONTROLLED_AND_DEMO)
    assert len(pop_e) == 10
    assert all(r.execution_source in (ExecutionSource.SYNTHETIC_MOCK, ExecutionSource.DEMO_HARNESS, ExecutionSource.CONTROLLED_DEFECT) for r in pop_e)


def test_stream_isolation_and_target_provenance_integrity():
    """
    Verifies Slice 6.7.1 Dataset Integrity:
    1. Temporal transitions are strictly formed within the same logical prediction stream (test_case_id, execution_source).
    2. Interleaving an AI Agent run into a Playwright test case sequence does NOT create cross-runner transitions.
    3. An isolated single run produces 0 transitions (NO_DATA), never 1 transition.
    4. Feature vectors record both execution_source and target_execution_source, target_run_id != run_id, and t_feature < t_target.
    """
    from backend.app.models.enums import DatasetStatus

    # Create 4 Playwright runs on tc_eda_health_smoke
    pw_runs = [
        TestRun(
            run_id=f"run_pw_{i}",
            application_id="target_eda",
            test_case_id="tc_eda_health_smoke",
            runner_type=RunnerType.PLAYWRIGHT,
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            status=RunStatus.PASSED if i % 2 == 0 else RunStatus.FAILED,
            started_at=f"2026-09-24T14:0{i}:00Z",
        )
        for i in range(4)
    ]

    # Interleave 1 AI Agent run chronologically between run_pw_1 and run_pw_2
    ai_run = TestRun(
        run_id="run_ai_isolated",
        application_id="target_eda",
        test_case_id="tc_eda_health_smoke",
        runner_type=RunnerType.AI_AGENT,
        execution_source=ExecutionSource.REAL_AI_AGENT,
        status=RunStatus.FAILED,
        started_at="2026-09-24T14:01:30Z",
    )

    all_test_runs = pw_runs[:2] + [ai_run] + pw_runs[2:]

    # Extract reliability records
    records = [
        ReliabilityFeatureExtractor.extract_record_from_run(r, evidence_items=[], failures=[])
        for r in all_test_runs
    ]

    # Build temporal dataset
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    # 1. Total records = 5 (4 PW + 1 AI)
    # 2. PW has 4 runs -> 3 transitions (t0->t1, t1->t2, t2->t3, last has label None)
    # 3. AI has 1 run -> 0 transitions (label None)
    # Total vectors with label_next_failed != None MUST be 3!
    usable_vectors = [v for v in vectors if v.label_next_failed is not None]
    assert len(usable_vectors) == 3

    # Check that AI Agent vector has NO target label
    ai_vector = next(v for v in vectors if v.run_id == "run_ai_isolated")
    assert ai_vector.label_next_failed is None
    assert ai_vector.target_run_id is None
    assert ai_vector.target_execution_source is None

    # Check each Playwright transition has strict provenance and chronological validity
    for v in usable_vectors:
        assert v.execution_source == ExecutionSource.REAL_PLAYWRIGHT
        assert v.target_execution_source == ExecutionSource.REAL_PLAYWRIGHT
        assert v.target_run_id is not None
        assert v.target_run_id != v.run_id
        assert v.target_run_id.startswith("run_pw_")

    # Check Population Audits
    audit_pw = PopulationSeparator.audit_population(
        PopulationType.REAL_PLAYWRIGHT_ONLY, records, vectors
    )
    assert audit_pw.total_runs == 4
    assert audit_pw.total_transitions == 3

    audit_ai = PopulationSeparator.audit_population(
        PopulationType.REAL_AI_AGENT_ONLY, records, vectors
    )
    assert audit_ai.total_runs == 1
    assert audit_ai.total_transitions == 0
    assert audit_ai.status == DatasetStatus.NO_DATA
    assert "Zero usable temporal transitions" in audit_ai.status_reason

    audit_real = PopulationSeparator.audit_population(
        PopulationType.REAL_EXECUTIONS_ONLY, records, vectors
    )
    assert audit_real.total_runs == 5
    assert audit_real.total_transitions == 3

