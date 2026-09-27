import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import (
    TestRun,
    TestAction,
    Evidence,
    Failure,
    EngineeringDiagnosis,
    DiagnosisClaim,
    RemediationTask,
    RemediationAttempt,
    RegressionVerification,
    RunStatus,
    RunnerType,
    TestMode,
    FailureCategory,
    Severity,
    ClaimType,
    GroundingStatus,
    RemediationStatus,
    TrendStatus,
    RiskBand,
    PredictionStatus,
    ReliabilityRecord,
)

from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.reliability_model import (
    LogisticReliabilityModel,
    BaseBaselinePredictor,
)
from backend.app.models.reliability import ReliabilityFeatureVector
from backend.app.services.reliability_service import ReliabilityService


def test_feature_extraction_without_temporal_leakage():
    """Validates that feature extraction correctly calculates rolling history and preserves temporal non-leakage."""
    now = datetime.now(timezone.utc)
    records = []

    # Create 4 consecutive runs for test_case_001
    for i in range(4):
        t = (now + timedelta(minutes=i * 10)).isoformat()
        is_fail = 1 if i in (1, 2) else 0
        status = RunStatus.FAILED.value if is_fail else RunStatus.PASSED.value

        rec = ReliabilityFeatureExtractor.extract_record_from_run(
            run=TestRun(
                run_id=f"run_{i}",
                application_id="app_1",
                application_version="1.0.0",
                test_mode=TestMode.FUNCTIONAL_QA,
                runner_type=RunnerType.PLAYWRIGHT,
                test_case_id="tc_001",
                status=status,
                started_at=t,
                duration_ms=1000 + i * 200,
                environment_id="env_1",
                actions=[TestAction(action_id=f"a_{i}", action_type="NAVIGATE", description="nav", timestamp=t, status="PASSED", input_data={}, output_data={}, duration_ms=100, evidence_ids=[])],
                evidence_ids=[],
                failure_ids=[],
                metrics_summary={},
                logs=[],
                created_at=t,
            ),
            evidence_items=[],
            failures=[Failure(failure_id=f"f_{i}", run_id=f"run_{i}", category=FailureCategory.ASSERTION_FAILURE, severity=Severity.HIGH, title="Fail", message="Fail", timestamp=t)] if is_fail else [],
            diagnosis=None,
            remediation_task=None,
        )
        records.append(rec)

    temporal_vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    assert len(temporal_vectors) == 4

    # Row 0: first run, no prior history (only 1 run in past)
    assert temporal_vectors[0].features["historical_fail_rate"] == 0.0
    # Next run was i=1 which failed (1)
    assert temporal_vectors[0].label_next_failed == 1

    # Row 1: 2 runs in past (1 pass, 1 fail)
    assert temporal_vectors[1].features["historical_fail_rate"] == 0.5
    # Next run was i=2 which failed (1)
    assert temporal_vectors[1].label_next_failed == 1

    # Row 2: 3 runs in past (1 pass, 2 fails)
    assert round(temporal_vectors[2].features["historical_fail_rate"], 2) == 0.67
    # Next run was i=3 which passed (0)
    assert temporal_vectors[2].label_next_failed == 0

    # Row 3: Latest run, no future run exists yet (label_next_failed must be None!)
    assert temporal_vectors[3].label_next_failed is None
    assert temporal_vectors[3].features["historical_fail_rate"] == 0.5




def test_baseline_predictors():
    """Validates simple deterministic baseline predictors."""
    vec = ReliabilityFeatureVector(
        run_id="r1",
        target_id="t1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        features={
            "failed_step_count": 1.0,
            "recent_fail_rate_3": 0.67,
            "historical_fail_rate": 0.60,
            "consecutive_fails": 1.0,
        }
    )

    assert BaseBaselinePredictor.predict_last_status(vec) == 1.0
    assert BaseBaselinePredictor.predict_moving_average(vec) == 0.67
    assert BaseBaselinePredictor.predict_historical_frequency(vec) == 0.60



def test_small_dataset_policy_insufficient_data():
    """Validates that ML model does not fabricate predictions on small datasets."""
    model = LogisticReliabilityModel()
    
    # Train with 3 samples (< 5 threshold)
    now = datetime.now(timezone.utc).isoformat()
    sparse_records = []
    for i in range(3):
        rec = ReliabilityFeatureExtractor.extract_record_from_run(
            run=TestRun(
                run_id=f"r_sparse_{i}",
                application_id="app_1",
                application_version="1.0.0",
                test_mode=TestMode.FUNCTIONAL_QA,
                runner_type=RunnerType.MOCK,
                test_case_id="tc_sparse",
                status=RunStatus.PASSED.value,
                started_at=now,
                duration_ms=500,
                environment_id="env_1",
                actions=[],
                evidence_ids=[],
                failure_ids=[],
                metrics_summary={},
                logs=[],
                created_at=now,
            ),
            evidence_items=[],
            failures=[],
            diagnosis=None,
            remediation_task=None,
        )
        sparse_records.append(rec)

    dataset = ReliabilityFeatureExtractor.build_temporal_dataset(sparse_records)
    metrics = model.fit(dataset)

    assert metrics.status in (PredictionStatus.INSUFFICIENT_DATA, PredictionStatus.NO_DATA)
    assert model.is_trained is False

    # Inference should return INSUFFICIENT_DATA without crashing
    pred = model.predict_test_case(dataset[0], test_case_name="Sparse Test", total_historical_runs=3)
    assert pred.status == PredictionStatus.INSUFFICIENT_DATA
    assert pred.prediction_available is False
    assert pred.risk_band == RiskBand.UNKNOWN
    assert len(pred.limitations) > 0


def test_logistic_reliability_model_training_and_inference():
    """Validates training on chronological sequences and interpretable prediction outputs."""
    model = LogisticReliabilityModel()
    now = datetime.now(timezone.utc)
    records = []

    # Build sequence of 12 runs with clear predictive signals
    for i in range(12):
        t = (now + timedelta(hours=i)).isoformat()
        is_fail = 1 if (i % 2 == 1 or i >= 8) else 0
        status = RunStatus.FAILED.value if is_fail else RunStatus.PASSED.value

        rec = ReliabilityFeatureExtractor.extract_record_from_run(
            run=TestRun(
                run_id=f"r_train_{i}",
                application_id="app_1",
                application_version="1.0.0",
                test_mode=TestMode.FUNCTIONAL_QA,
                runner_type=RunnerType.PLAYWRIGHT,
                test_case_id="tc_train_1",
                status=status,
                started_at=t,
                duration_ms=2000 + i * 100,
                environment_id="env_1",
                actions=[],
                evidence_ids=[],
                failure_ids=[],
                metrics_summary={},
                logs=[],
                created_at=t,
            ),
            evidence_items=[],
            failures=[Failure(failure_id=f"f_{i}", run_id=f"r_train_{i}", category=FailureCategory.ASSERTION_FAILURE, severity=Severity.HIGH, title="Fail", message="Fail", timestamp=t)] if is_fail else [],
            diagnosis=None,
            remediation_task=None,
        )
        records.append(rec)

    dataset = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    metrics = model.fit(dataset)

    assert metrics.status == PredictionStatus.TRAINED
    assert model.is_trained is True
    assert metrics.accuracy is not None

    # Predict next state using latest vector
    latest_vec = dataset[-1]
    pred = model.predict_test_case(latest_vec, test_case_name="Train Test 1", total_historical_runs=12)

    assert pred.prediction_available is True
    assert pred.failure_probability is not None
    assert 0.0 <= pred.failure_probability <= 1.0
    assert pred.risk_band in (RiskBand.LOW, RiskBand.MEDIUM, RiskBand.HIGH)
    assert len(pred.contributing_features) > 0

    # Ensure baseline probabilities are calculated
    assert "last_status_prob" in pred.baseline_probabilities
    assert "moving_average_3_prob" in pred.baseline_probabilities
    assert "historical_frequency_prob" in pred.baseline_probabilities



def test_grounded_component_attribution_only():
    """Validates that only evidence-grounded component attributions are recorded in historical patterns."""
    repo = SQLiteRepository()
    now = datetime.now(timezone.utc).isoformat()
    import uuid
    uid = uuid.uuid4().hex[:6]

    run_ungrounded_id = f"run_ungrounded_{uid}"
    run_grounded_id = f"run_grounded_{uid}"

    # Create run with an UNGROUNDED diagnosis
    run_ungrounded = TestRun(
        run_id=run_ungrounded_id,
        application_id="app_test",
        application_version="1.0.0",
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.MOCK,
        test_case_id=f"tc_ungrounded_{uid}",
        status=RunStatus.FAILED.value,
        started_at=now,
        duration_ms=500,
        environment_id="env_1",
        actions=[],
        evidence_ids=[],
        failure_ids=[f"f_ungrounded_{uid}"],
        metrics_summary={},
        logs=[],
        created_at=now,
    )
    repo.create_run(run_ungrounded)
    repo.save_failure(Failure(failure_id=f"f_ungrounded_{uid}", run_id=run_ungrounded_id, category=FailureCategory.ASSERTION_FAILURE, severity=Severity.HIGH, title="Fail", message="Fail", timestamp=now))
    repo.save_diagnosis(EngineeringDiagnosis(
        diagnosis_id=f"diag_ungrounded_{uid}",
        run_id=run_ungrounded_id,
        title="Hallucinated Component",
        root_cause_summary="Ungrounded speculation",
        failure_category=FailureCategory.ASSERTION_FAILURE,
        confidence_score=0.3,
        suspected_component="FakeUngroundedComponent",
        deterministic_signals=[],
        reproduction_steps=[],
        suggested_fix="none",
        regression_test_spec="none",
        severity=Severity.HIGH,
        evidence_bundle_summary="none",
        is_grounded=False,
        grounded_suspected_component=None,
        created_at=now,
    ))

    # Create run with a GROUNDED diagnosis
    run_grounded = TestRun(
        run_id=run_grounded_id,
        application_id="app_test",
        application_version="1.0.0",
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.MOCK,
        test_case_id=f"tc_grounded_{uid}",
        status=RunStatus.FAILED.value,
        started_at=now,
        duration_ms=500,
        environment_id="env_1",
        actions=[],
        evidence_ids=[],
        failure_ids=[f"f_grounded_{uid}"],
        metrics_summary={},
        logs=[],
        created_at=now,
    )
    repo.create_run(run_grounded)
    repo.save_failure(Failure(failure_id=f"f_grounded_{uid}", run_id=run_grounded_id, category=FailureCategory.ASSERTION_FAILURE, severity=Severity.HIGH, title="Fail", message="Fail", timestamp=now))
    repo.save_diagnosis(EngineeringDiagnosis(
        diagnosis_id=f"diag_grounded_{uid}",
        run_id=run_grounded_id,
        title="Grounded Component Error",
        root_cause_summary="Verified component flaw",
        failure_category=FailureCategory.ASSERTION_FAILURE,
        confidence_score=0.9,
        suspected_component="VerifiedCalculationEngine",
        deterministic_signals=[],
        reproduction_steps=[],
        suggested_fix="Fix math",
        regression_test_spec="Assert result",
        severity=Severity.HIGH,
        evidence_bundle_summary="evidence present",
        is_grounded=True,
        grounded_suspected_component="VerifiedCalculationEngine",
        created_at=now,
    ))


    service = ReliabilityService(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        remediation_repo=repo,
    )

    patterns = service.get_failure_patterns()
    assert len(patterns) > 0
    all_top_components = [c for p in patterns for c in p.top_grounded_components]

    # Grounded component should be recorded
    assert "VerifiedCalculationEngine" in all_top_components
    # Ungrounded hallucinated component should NOT be recorded
    assert "FakeUngroundedComponent" not in all_top_components


def test_trend_analysis_deterministic_logic():
    """Validates trend analysis classification (IMPROVING, DEGRADING, STABLE, INSUFFICIENT_DATA)."""
    now = datetime.now(timezone.utc)
    service = ReliabilityService(
        run_repo=SQLiteRepository(),
        target_repo=SQLiteRepository(),
        test_case_repo=SQLiteRepository(),
        evidence_repo=SQLiteRepository(),
        failure_repo=SQLiteRepository(),
        diagnosis_repo=SQLiteRepository(),
        remediation_repo=SQLiteRepository(),
    )

    # 1. Insufficient data (< 3 runs)
    assert service.get_trends(records=[]).overall_trend == TrendStatus.INSUFFICIENT_DATA

    # 2. Degrading: historical was mostly pass (0), recent is all fail (1)
    degrading_records = []
    for i in range(10):
        t = (now + timedelta(minutes=i)).isoformat()
        is_fail = 1 if i >= 7 else 0
        rec = ReliabilityRecord(
            record_id=f"r_{i}", run_id=f"r_{i}", target_id="t1", timestamp=t, runner_type="MOCK",
            run_status="FAILED" if is_fail else "PASSED", duration_ms=500, step_count=1, failed_step_count=is_fail,
            assertion_failure_count=is_fail, console_error_count=0, network_error_count=0, http_4xx_count=0,
            http_5xx_count=0, navigation_failure_count=0, browser_error_count=0, agent_loop_detected=False,
            grounding_score=1.0, unsupported_claim_count=0, contradicted_claim_count=0, remediation_attempts=0,
            remediation_status=None, regression_detected=False, failure_label=is_fail,
        )
        degrading_records.append(rec)
    assert service.get_trends(records=degrading_records).overall_trend == TrendStatus.DEGRADING

    # 3. Improving: historical was fail (1), recent is all pass (0)
    improving_records = []
    for i in range(10):
        t = (now + timedelta(minutes=i)).isoformat()
        is_fail = 1 if i < 6 else 0
        rec = ReliabilityRecord(
            record_id=f"r_{i}", run_id=f"r_{i}", target_id="t1", timestamp=t, runner_type="MOCK",
            run_status="FAILED" if is_fail else "PASSED", duration_ms=500, step_count=1, failed_step_count=is_fail,
            assertion_failure_count=is_fail, console_error_count=0, network_error_count=0, http_4xx_count=0,
            http_5xx_count=0, navigation_failure_count=0, browser_error_count=0, agent_loop_detected=False,
            grounding_score=1.0, unsupported_claim_count=0, contradicted_claim_count=0, remediation_attempts=0,
            remediation_status=None, regression_detected=False, failure_label=is_fail,
        )
        improving_records.append(rec)
    assert service.get_trends(records=improving_records).overall_trend == TrendStatus.IMPROVING


def test_api_reliability_endpoints():
    """Validates FastAPI REST endpoints for historical reliability and predictive QA."""
    client = TestClient(app)

    # 1. Summary
    res = client.get("/api/v1/reliability/summary")
    assert res.status_code == 200
    summary = res.json()
    assert "total_runs" in summary
    assert "failure_rate" in summary
    assert "prediction_coverage_pct" in summary

    # 2. Trends
    res = client.get("/api/v1/reliability/trends")
    assert res.status_code == 200
    trends = res.json()
    assert "overall_trend" in trends
    assert "historical_failure_rate" in trends

    # 3. Failure Patterns
    res = client.get("/api/v1/reliability/failure-patterns")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 4. Predictions
    res = client.get("/api/v1/reliability/predictions")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 5. QA Prioritization
    res = client.get("/api/v1/reliability/prioritization")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 6. Model Training & Status
    res = client.post("/api/v1/reliability/train")
    assert res.status_code == 200
    train_res = res.json()
    assert "status" in train_res
    assert "model_version" in train_res

    res = client.get("/api/v1/reliability/model/status")
    assert res.status_code == 200
    status_res = res.json()
    assert "model_version" in status_res
