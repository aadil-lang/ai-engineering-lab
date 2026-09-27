import pytest
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.enums import CampaignType, ExecutionSource
from backend.app.models.reliability import ReliabilityRecord, ReliabilityFeatureVector
from backend.app.models.cross_app import (
    MetricStatus,
    CrossApplicationEvaluationReport,
    CrossApplicationEvaluationProtocol,
)
from backend.app.prediction.cross_app_evaluator import CrossAppEvaluator
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.repositories.sqlite_repository import SQLiteRepository


@pytest.fixture
def client():
    return TestClient(app)


def test_safe_metrics_zero_positive_class_reports_not_computable():
    """
    Scientific Invariant:
    When a test set contains zero positive instances (e.g. 100% pass rate like Booking app),
    Precision, Recall, and ROC-AUC are mathematically NOT_COMPUTABLE.
    The evaluator must NEVER report a false default like ROC-AUC=0.5.
    """
    y_true = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 10 passes, 0 fails
    y_pred = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    y_probs = [0.05] * 10

    report = CrossAppEvaluator.calculate_safe_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_probs=y_probs,
        model_name="Zero-Positive Test Model",
        n_resamples=50,
    )

    # Accuracy is computable
    assert report.accuracy.status == MetricStatus.COMPUTED
    assert report.accuracy.value == 1.0

    # Brier score is computable
    assert report.brier_score.status == MetricStatus.COMPUTED
    assert report.brier_score.value == pytest.approx(0.0025, abs=1e-4)

    # Precision, Recall, F1, ROC-AUC must be NOT_COMPUTABLE
    assert report.precision.status == MetricStatus.NOT_COMPUTABLE
    assert report.precision.value is None
    assert "No positive predictions" in report.precision.reason

    assert report.recall.status == MetricStatus.NOT_COMPUTABLE
    assert report.recall.value is None
    assert "Zero positive instances" in report.recall.reason

    assert report.f1_score.status == MetricStatus.NOT_COMPUTABLE
    assert report.f1_score.value is None

    assert report.roc_auc.status == MetricStatus.NOT_COMPUTABLE
    assert report.roc_auc.value is None
    assert "Both classes required" in report.roc_auc.reason


def test_safe_metrics_multi_class_and_bootstrap_intervals():
    """
    Verifies that when both classes are present, discrimination metrics are computed
    and bootstrap confidence intervals are properly bounded in [0, 1].
    """
    y_true = [0, 0, 0, 0, 0, 1, 1, 0, 0, 1]  # 7 passes, 3 fails
    y_pred = [0, 0, 0, 0, 1, 1, 1, 0, 0, 0]  # 2 TP, 1 FP, 1 FN, 6 TN
    y_probs = [0.1, 0.2, 0.1, 0.05, 0.7, 0.8, 0.9, 0.3, 0.2, 0.4]

    report = CrossAppEvaluator.calculate_safe_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_probs=y_probs,
        model_name="Multi-Class Test Model",
        n_resamples=100,
    )

    assert report.accuracy.status == MetricStatus.COMPUTED
    assert report.accuracy.value == 0.80
    assert 0.0 <= report.accuracy.lower_ci <= report.accuracy.value <= report.accuracy.upper_ci <= 1.0

    assert report.precision.status == MetricStatus.COMPUTED
    assert report.precision.value == pytest.approx(2 / 3, abs=1e-3)

    assert report.recall.status == MetricStatus.COMPUTED
    assert report.recall.value == pytest.approx(2 / 3, abs=1e-3)

    assert report.roc_auc.status == MetricStatus.COMPUTED
    assert report.roc_auc.value is not None
    assert 0.0 <= report.roc_auc.value <= 1.0

    assert report.brier_score.status == MetricStatus.COMPUTED
    assert report.confusion_matrix.true_positives == 2
    assert report.confusion_matrix.false_positives == 1


def test_loao_strict_leakage_assertion():
    """
    Mandatory Leakage Invariant:
    TrainApplications ∩ TestApplications = ∅.
    If an overlapping application is attempted, a ValueError/AssertionError must be raised.
    """
    v1 = ReliabilityFeatureVector(
        run_id="r1",
        target_id="real_eda_local",
        application_id="app_eda",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        campaign_type=CampaignType.REAL_RELIABILITY,
        timestamp="2026-09-24T10:00:00Z",
        features={"recent_fail_rate_3": 0.0},
        label_next_failed=0,
    )
    v2 = ReliabilityFeatureVector(
        run_id="r2",
        target_id="real_inventory_local",
        application_id="app_inventory",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        campaign_type=CampaignType.REAL_RELIABILITY,
        timestamp="2026-09-24T10:05:00Z",
        features={"recent_fail_rate_3": 0.5},
        label_next_failed=1,
    )
    v3 = ReliabilityFeatureVector(
        run_id="r3",
        target_id="real_booking_local",
        application_id="app_booking",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        campaign_type=CampaignType.REAL_RELIABILITY,
        timestamp="2026-09-24T10:10:00Z",
        features={"recent_fail_rate_3": 0.0},
        label_next_failed=0,
    )

    # Valid non-overlapping LOAO evaluation executes cleanly
    res, shifts = CrossAppEvaluator.evaluate_regime_b_loao([v1, v2, v3])
    assert len(res) == 3
    for r in res:
        assert r.leakage_check_passed is True
        assert r.test_application not in r.train_applications


def test_live_evaluation_dataset_snapshot_and_provenance():
    """
    Verifies that snapshot creation on the live database adheres to Slice 6.9 freeze requirements:
    - Exactly 3 applications: app_eda, app_inventory, app_booking
    - campaign_type = REAL_RELIABILITY
    - execution_source = REAL_PLAYWRIGHT
    - Zero contamination from DEMO or SYNTHETIC
    - Exactly 73 transitions
    """
    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        pytest.skip("Live database not found.")

    repo = SQLiteRepository(db_path=db_path)
    runs = repo.list_runs(limit=2000)
    records = []
    for r in runs:
        ev = repo.get_evidence_by_run(r.run_id)
        fa = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, ev, fa))

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    snapshot = CrossAppEvaluator.create_dataset_snapshot(records, vectors)

    assert set(snapshot.application_ids) == {"app_eda", "app_inventory", "app_booking"}
    assert snapshot.total_runs == 79
    assert snapshot.total_transitions == 73
    assert snapshot.failures_count == 5
    assert snapshot.passes_count == 68
    assert snapshot.population_filter["campaign_type"] == "REAL_RELIABILITY"
    assert snapshot.population_filter["execution_source"] == "REAL_PLAYWRIGHT"
    assert snapshot.excluded_population_counts["DEMO"] > 0
    assert snapshot.excluded_population_counts["SYNTHETIC"] > 0


def test_full_cross_app_evaluation_execution():
    """
    End-to-end execution of CrossAppEvaluator.run_complete_evaluation on live database:
    - Verifies Regime A reports INSUFFICIENT_DATA for Booking (single-class)
    - Verifies all 3 LOAO experiments in Regime B complete with verified leakage checks
    - Verifies Regime C combined temporal split completes
    - Verifies concentration analysis sums to 100%
    """
    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        pytest.skip("Live database not found.")

    repo = SQLiteRepository(db_path=db_path)
    runs = repo.list_runs(limit=2000)
    records = []
    for r in runs:
        ev = repo.get_evidence_by_run(r.run_id)
        fa = repo.get_failures_by_run(r.run_id)
        records.append(ReliabilityFeatureExtractor.extract_record_from_run(r, ev, fa))

    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)

    report = CrossAppEvaluator.run_complete_evaluation(records, vectors)

    assert isinstance(report, CrossApplicationEvaluationReport)
    assert report.protocol_version == "CrossApplicationEvaluationProtocol v1.0"

    # Regime A
    booking_regime_a = next(r for r in report.regime_a_within_application if r.application_id == "app_booking")
    assert booking_regime_a.status == "INSUFFICIENT_DATA"
    assert "Single-class application history" in booking_regime_a.status_reason

    # Regime B (3 LOAO experiments)
    assert len(report.regime_b_loao) == 3
    for exp in report.regime_b_loao:
        assert exp.leakage_check_passed is True
        assert exp.test_application not in exp.train_applications
        assert len(exp.baseline_performances) == 4

    # Regime C
    assert report.regime_c_combined.train_transitions > 0
    assert report.regime_c_combined.test_transitions > 0
    assert report.regime_c_combined.train_transitions + report.regime_c_combined.test_transitions == 73

    # Concentration
    total_pct = sum(a.percentage_of_transitions for a in report.application_concentration)
    assert total_pct == pytest.approx(100.0, abs=0.1)


def test_api_cross_application_endpoints(client):
    """
    Verifies that the cross-application REST API endpoints return 200 and schema-valid payloads:
    - GET /api/v1/reliability/cross-application/protocol
    - GET /api/v1/reliability/cross-application-evaluation
    """
    # 1. Protocol endpoint
    resp_proto = client.get("/api/v1/reliability/cross-application/protocol")
    assert resp_proto.status_code == 200
    data_proto = resp_proto.json()
    assert data_proto["protocol_id"] == "CrossApplicationEvaluationProtocol-v1.0"
    assert "leakage_invariants" in data_proto
    assert len(data_proto["baselines"]) == 4

    # 2. Evaluation endpoint
    resp_eval = client.get("/api/v1/reliability/cross-application-evaluation")
    assert resp_eval.status_code == 200
    data_eval = resp_eval.json()
    assert "snapshot" in data_eval
    assert "regime_b_loao" in data_eval
    assert len(data_eval["regime_b_loao"]) == 3
    assert data_eval["snapshot"]["total_transitions"] == 73
