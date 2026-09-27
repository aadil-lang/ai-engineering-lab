import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.enums import (
    ExecutionSource,
    PopulationType,
    DatasetStatus,
    RunnerType,
    RunStatus,
)
from backend.app.models.test_run import TestRun
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilityFeatureVector,
    PopulationAuditSummary,
    WalkForwardEvaluationReport,
    PopulationSeparationReport,
)
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.walk_forward_evaluator import (
    PopulationSeparator,
    WalkForwardEvaluator,
    ProductionReliabilityDatasetAnalyzer,
    POPULATION_DEFINITIONS,
)


@pytest.fixture
def api_client():
    return TestClient(app)


def test_execution_source_classification():
    """Verifies deterministic classification of execution source based on runner and metadata."""
    # Playwright runner on real target
    run_playwright = TestRun(
        run_id="run_pw_1",
        application_id="app_eng_automation",
        name="Real Playwright Flow",
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_playwright) == ExecutionSource.REAL_PLAYWRIGHT

    # AI Agent runner
    run_ai = TestRun(
        run_id="run_ai_1",
        application_id="app_eng_automation",
        name="Autonomous Exploratory Agent",
        runner_type=RunnerType.AI_AGENT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_ai) == ExecutionSource.REAL_AI_AGENT

    # Demo shop harness with explicit provenance
    run_demo = TestRun(
        run_id="run_demo_1",
        application_id="target_tgt_demo_shop",
        execution_source=ExecutionSource.DEMO_HARNESS,
        name="Demo Shop Regression",
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_demo) == ExecutionSource.DEMO_HARNESS

    # Controlled defect injection with explicit provenance
    run_defect = TestRun(
        run_id="run_def_1",
        application_id="app_eng_automation",
        execution_source=ExecutionSource.CONTROLLED_DEFECT,
        natural_language_goal="Controlled Defect Experiment Run",
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.FAILED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_defect) == ExecutionSource.CONTROLLED_DEFECT

    # Synthetic mock runner defaults to SYNTHETIC_MOCK
    run_mock = TestRun(
        run_id="run_mock_1",
        application_id="app_generic",
        natural_language_goal="Mock Unit Run",
        runner_type=RunnerType.MOCK,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_mock) == ExecutionSource.SYNTHETIC_MOCK

    # Verifies provenance is NOT inferred from target name or URL keywords
    run_demo_pw = TestRun(
        run_id="run_demo_pw_real",
        application_id="target_tgt_demo_shop",
        runner_type=RunnerType.PLAYWRIGHT,
        status=RunStatus.PASSED,
    )
    assert ReliabilityFeatureExtractor.classify_execution_source(run_demo_pw) == ExecutionSource.REAL_PLAYWRIGHT


def test_population_filtering_and_audit():
    """Verifies population filtering correctly segregates execution sources without leakage."""
    records = [
        ReliabilityRecord(
            run_id="r1", target_id="t1", timestamp="2026-09-01T00:00:00Z",
            execution_source=ExecutionSource.REAL_PLAYWRIGHT, failure_label=0
        ),
        ReliabilityRecord(
            run_id="r2", target_id="t1", timestamp="2026-09-01T01:00:00Z",
            execution_source=ExecutionSource.REAL_AI_AGENT, failure_label=1
        ),
        ReliabilityRecord(
            run_id="r3", target_id="demo", timestamp="2026-09-01T02:00:00Z",
            execution_source=ExecutionSource.DEMO_HARNESS, failure_label=0
        ),
        ReliabilityRecord(
            run_id="r4", target_id="mock", timestamp="2026-09-01T03:00:00Z",
            execution_source=ExecutionSource.SYNTHETIC_MOCK, failure_label=1
        ),
    ]
    vectors = [
        ReliabilityFeatureVector(
            run_id="r1", target_id="t1", timestamp="2026-09-01T00:00:00Z",
            execution_source=ExecutionSource.REAL_PLAYWRIGHT, label_next_failed=1
        ),
        ReliabilityFeatureVector(
            run_id="r2", target_id="t1", timestamp="2026-09-01T01:00:00Z",
            execution_source=ExecutionSource.REAL_AI_AGENT, label_next_failed=0
        ),
        ReliabilityFeatureVector(
            run_id="r3", target_id="demo", timestamp="2026-09-01T02:00:00Z",
            execution_source=ExecutionSource.DEMO_HARNESS, label_next_failed=1
        ),
    ]


    # Filter Population B (Real only)
    real_records = PopulationSeparator.filter_records_by_population(records, PopulationType.REAL_EXECUTIONS_ONLY)
    assert len(real_records) == 2
    assert all(r.execution_source in (ExecutionSource.REAL_PLAYWRIGHT, ExecutionSource.REAL_AI_AGENT) for r in real_records)

    # Filter Population E (Demo / Mock)
    demo_records = PopulationSeparator.filter_records_by_population(records, PopulationType.CONTROLLED_AND_DEMO)
    assert len(demo_records) == 2
    assert all(r.execution_source in (ExecutionSource.DEMO_HARNESS, ExecutionSource.SYNTHETIC_MOCK) for r in demo_records)

    # Audit Population B with insufficient data
    audit_b = PopulationSeparator.audit_population(PopulationType.REAL_EXECUTIONS_ONLY, records, vectors)
    assert audit_b.total_runs == 2
    assert audit_b.status == DatasetStatus.INSUFFICIENT_DATA


def test_walk_forward_evaluation_insufficient_data():
    """Verifies WalkForwardEvaluator gracefully returns INSUFFICIENT_DATA when sample size is below threshold."""
    # Only 5 transitions when min_train_size=20, step_size=5
    vectors = [
        ReliabilityFeatureVector(
            run_id=f"r_{i}",
            target_id="t1",
            timestamp=f"2026-09-01T0{i}:00:00Z",
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            features={"failed_step_count": 0.0},
            label_next_failed=i % 2,
        )
        for i in range(5)
    ]
    report = WalkForwardEvaluator.run_walk_forward_evaluation(
        vectors=vectors,
        population=PopulationType.REAL_PLAYWRIGHT_ONLY,
        min_train_size=20,
        step_size=5,
    )
    assert report.status == "INSUFFICIENT_DATA"
    assert report.num_folds == 0
    assert len(report.folds) == 0


def test_walk_forward_expanding_window_and_aggregates():
    """Verifies that expanding window cross-validation runs without lookahead bias across folds."""
    # Create 35 synthetic transitions
    vectors: list[ReliabilityFeatureVector] = []
    for i in range(35):
        hour = i % 24
        day = 1 + (i // 24)
        ts = f"2026-09-0{day}T{hour:02d}:00:00Z"
        y_next = 1 if (i % 3 == 0) else 0
        vectors.append(
            ReliabilityFeatureVector(
                run_id=f"run_{i:03d}",
                target_id="test_suite_1",
                timestamp=ts,
                execution_source=ExecutionSource.CONTROLLED_DEFECT,
                features={
                    "consecutive_fails": float(i % 2),
                    "failed_step_count": float(i % 3),
                    "error_log_density": 0.5 if (i % 3 == 0) else 0.0,
                    "recent_fail_rate_3": 0.33,
                    "historical_fail_rate": 0.33,
                },
                label_next_failed=y_next,
            )
        )

    min_train = 20
    step = 5
    report = WalkForwardEvaluator.run_walk_forward_evaluation(
        vectors=vectors,
        population=PopulationType.CONTROLLED_AND_DEMO,
        min_train_size=min_train,
        step_size=step,
    )

    assert report.status == "EVALUATED"
    assert report.num_folds == 3  # (35 - 20) / 5 = 3 folds
    assert len(report.folds) == 3

    # Check Fold 0: Train [0:20], Test [20:25]
    f0 = report.folds[0]
    assert f0.train_sample_count == 20
    assert f0.test_sample_count == 5
    assert f0.fold_index == 0

    # Check Fold 1: Train [0:25], Test [25:30]
    f1 = report.folds[1]
    assert f1.train_sample_count == 25
    assert f1.test_sample_count == 5
    assert f1.fold_index == 1

    # Check Fold 2: Train [0:30], Test [30:35]
    f2 = report.folds[2]
    assert f2.train_sample_count == 30
    assert f2.test_sample_count == 5
    assert f2.fold_index == 2

    # Check model aggregates are populated
    agg_ids = [a.model_id for a in report.model_aggregates]
    assert "v1.0" in agg_ids
    assert "v1.1" in agg_ids
    assert "v1.2" in agg_ids
    assert "majority_baseline" in agg_ids
    assert "prevalence_baseline" in agg_ids
    assert "random_baseline" in agg_ids

    for agg in report.model_aggregates:
        assert agg.mean_accuracy is not None
        assert 0.0 <= agg.mean_accuracy <= 1.0
        assert agg.mean_brier_score is not None
        assert 0.0 <= agg.mean_brier_score <= 1.0


def test_api_population_separation_endpoint(api_client):
    """Tests GET /api/v1/reliability/population-separation endpoint."""
    resp = api_client.get("/api/v1/reliability/population-separation?min_train_size=20&step_size=5")
    assert resp.status_code == 200
    data = resp.json()

    assert "total_runs" in data
    assert "total_transitions" in data
    assert "source_breakdown" in data
    assert "populations" in data
    assert len(data["populations"]) == 5
    assert "walk_forward_reports" in data
    assert "ALL_HISTORICAL" in data["walk_forward_reports"]


def test_api_walk_forward_evaluation_endpoint(api_client):
    """Tests GET /api/v1/reliability/walk-forward-evaluation endpoint."""
    resp = api_client.get("/api/v1/reliability/walk-forward-evaluation?population=ALL_HISTORICAL&min_train_size=20&step_size=5")
    assert resp.status_code == 200
    data = resp.json()

    assert data["population"] == "ALL_HISTORICAL"
    assert "total_samples" in data
    assert "num_folds" in data
    assert "model_aggregates" in data
    assert "folds" in data
