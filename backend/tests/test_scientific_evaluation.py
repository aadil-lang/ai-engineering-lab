import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.enums import (
    RunStatus,
    TestMode,
    RunnerType,
    DatasetStatus,
    EvaluationSplitType,
    PredictionEvaluationStatus,
    RiskBand,
)
from backend.app.models.test_run import TestRun
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilityFeatureVector,
    PredictionRecord,
)
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.reliability_model import LogisticReliabilityModel, BaseBaselinePredictor
from backend.app.prediction.scientific_evaluator import ScientificEvaluator
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.services.reliability_service import ReliabilityService

import tempfile
import os

@pytest.fixture
def repo():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_eval.db")
    repository = SQLiteRepository(db_path=db_path)
    yield repository
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

@pytest.fixture
def sample_records():
    """Generates 10 sequential genuine historical QA execution records for 2 test cases."""
    base_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    records = []
    
    # Test case 1: 6 executions (Fail, Pass, Fail, Fail, Pass, Pass)
    tc1_outcomes = [1, 0, 1, 1, 0, 0]
    for i, fail in enumerate(tc1_outcomes):
        t = (base_time + timedelta(hours=i)).isoformat()
        records.append(
            ReliabilityRecord(
                run_id=f"run_tc1_{i+1}",
                target_id="target_eda",
                test_case_id="tc_eda_01",
                timestamp=t,
                run_status="FAILED" if fail else "COMPLETED",
                failure_label=fail,
                duration_ms=1200 + i * 50,
                assertion_failure_count=1 if fail else 0,
                http_5xx_count=0,
                console_error_count=1 if fail else 0,
                grounding_score=1.0,
                regression_detected=False,
            )
        )

    # Test case 2: 4 executions (Pass, Pass, Fail, Pass)
    tc2_outcomes = [0, 0, 1, 0]
    for i, fail in enumerate(tc2_outcomes):
        t = (base_time + timedelta(hours=i + 10)).isoformat()
        records.append(
            ReliabilityRecord(
                run_id=f"run_tc2_{i+1}",
                target_id="target_eda",
                test_case_id="tc_eda_02",
                timestamp=t,
                run_status="FAILED" if fail else "COMPLETED",
                failure_label=fail,
                duration_ms=900 + i * 30,
                assertion_failure_count=1 if fail else 0,
                http_5xx_count=0,
                console_error_count=0,
                grounding_score=1.0,
                regression_detected=False,
            )
        )

    return records


# ==========================================
# 1. Dataset Audit Tests
# ==========================================

def test_audit_empty_dataset():
    report = ScientificEvaluator.audit_dataset([])
    assert report.total_runs == 0
    assert report.status == DatasetStatus.NO_DATA
    assert "Zero historical QA executions" in report.status_reason


def test_audit_single_execution_dataset():
    records = [
        ReliabilityRecord(
            run_id="run_single_1",
            target_id="target_1",
            test_case_id="tc_1",
            timestamp="2026-09-24T10:00:00Z",
            run_status="COMPLETED",
            failure_label=0,
            duration_ms=1000,
        )
    ]
    report = ScientificEvaluator.audit_dataset(records)
    assert report.total_runs == 1
    assert report.total_usable_prediction_samples == 0
    assert report.single_execution_test_cases_count == 1
    assert report.status == DatasetStatus.INSUFFICIENT_DATA


def test_audit_genuine_dataset(sample_records):
    report = ScientificEvaluator.audit_dataset(sample_records)
    assert report.total_runs == 10
    assert report.failed_runs == 4
    assert report.passed_runs == 6
    assert report.unique_test_cases_count == 2
    # TC1 has 6 runs (5 transitions), TC2 has 4 runs (3 transitions) -> Total 8 transitions
    assert report.total_usable_prediction_samples == 8
    assert report.status == DatasetStatus.USABLE
    assert report.positive_labels_count > 0
    assert report.negative_labels_count > 0


# ==========================================
# 2. Temporal Non-Leakage & Provenance Tests
# ==========================================

def test_provenance_strict_chronological_ordering(sample_records):
    provenance = ScientificEvaluator.build_provenance_records(sample_records)
    assert len(provenance) == 8  # 5 from TC1, 3 from TC2
    
    for p in provenance:
        assert p.feature_timestamp < p.target_timestamp
        assert p.feature_run_id != p.target_run_id
        assert p.target_label in (0, 1)
        assert len(p.feature_names) > 0


def test_temporal_dataset_no_future_leakage(sample_records):
    """Verifies that features for execution t only use information up to t, never t+1."""
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(sample_records)
    assert len(vectors) == 10

    # Check that each vector's label matches the NEXT execution's outcome
    # For TC1: outcomes = [1, 0, 1, 1, 0, 0]
    # transitions: 0->1 (next is 0), 1->2 (next is 1), 2->3 (next is 1), 3->4 (next is 0), 4->5 (next is 0), 5 (None)
    tc1_vectors = [v for v in vectors if v.test_case_id == "tc_eda_01"]
    assert len(tc1_vectors) == 6
    assert tc1_vectors[0].label_next_failed == 0
    assert tc1_vectors[1].label_next_failed == 1
    assert tc1_vectors[2].label_next_failed == 1
    assert tc1_vectors[3].label_next_failed == 0
    assert tc1_vectors[4].label_next_failed == 0
    assert tc1_vectors[5].label_next_failed is None  # Latest has no subsequent run yet

    # Verify historical failure rate in vector does not use future runs
    assert tc1_vectors[0].features["historical_fail_rate"] == 1.0  # 1/1
    assert tc1_vectors[1].features["historical_fail_rate"] == 0.5  # 1/2
    assert round(tc1_vectors[2].features["historical_fail_rate"], 2) == 0.67  # 2/3


# ==========================================
# 3. Chronological Splits Tests
# ==========================================

def test_chronological_splits_ordering(sample_records):
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(sample_records)
    train, val, test = ScientificEvaluator.create_chronological_splits(vectors)
    
    assert len(train) > 0
    assert len(val) > 0
    assert len(test) > 0

    # Ensure max(train) <= min(val) and max(val) <= min(test)
    assert max(v.timestamp for v in train) <= min(v.timestamp for v in val)
    assert max(v.timestamp for v in val) <= min(v.timestamp for v in test)


# ==========================================
# 4. Baselines and Model Evaluation Tests
# ==========================================

def test_baselines_evaluation(sample_records):
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(sample_records)
    labelled = [v for v in vectors if v.label_next_failed is not None]
    baselines = ScientificEvaluator.evaluate_baselines(labelled)
    
    assert len(baselines) == 3
    b_ids = {b.baseline_id for b in baselines}
    assert "baseline_a" in b_ids
    assert "baseline_b" in b_ids
    assert "baseline_c" in b_ids

    for b in baselines:
        assert b.metrics.accuracy is not None
        assert 0.0 <= b.metrics.accuracy <= 1.0
        assert b.metrics.sample_count == len(labelled)


def test_classification_metrics_single_class():
    """Verifies that single-class test evaluation does not crash and marks ROC-AUC as N/A."""
    y_true = [0, 0, 0, 0]
    y_prob = [0.1, 0.2, 0.3, 0.4]
    metrics = ScientificEvaluator.calculate_classification_metrics(y_true, y_prob)
    assert metrics.sample_count == 4
    assert metrics.accuracy == 1.0
    assert metrics.roc_auc is None
    assert len(metrics.notes) > 0


# ==========================================
# 5. Probability Calibration Tests
# ==========================================

def test_calibration_small_sample():
    cal = ScientificEvaluator.evaluate_calibration([0, 1], [0.2, 0.8])
    assert not cal.is_evaluated
    assert cal.status == "INSUFFICIENT_DATA"


def test_calibration_sufficient_sample():
    y_true = [0, 1, 0, 1, 1, 0, 1, 0]
    y_prob = [0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.85, 0.15]
    cal = ScientificEvaluator.evaluate_calibration(y_true, y_prob, n_bins=5)
    assert cal.is_evaluated
    assert cal.brier_score is not None
    assert cal.brier_score < 0.15  # Good predictions have low Brier score
    assert cal.expected_calibration_error is not None
    assert len(cal.reliability_diagram_bins) == 5


# ==========================================
# 6. Prediction Tracking Lifecycle Tests
# ==========================================

def test_prediction_record_lifecycle(repo):
    service = ReliabilityService(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        remediation_repo=repo,
        prediction_record_repo=repo,
    )

    # 1. Record pending prediction for test case
    pred_rec = service.record_prediction(
        test_case_id="tc_eda_01",
        test_case_name="Engineering EDA Test",
        feature_run_id="run_001",
        predicted_failure_probability=0.75,
        predicted_risk_band=RiskBand.HIGH,
        prediction_class=1,
    )
    assert pred_rec.evaluation_status == PredictionEvaluationStatus.PENDING
    assert pred_rec.actual_outcome is None

    # Verify retrieved from repository
    pending = repo.get_pending_predictions_for_test_case("tc_eda_01")
    assert len(pending) == 1
    assert pending[0].prediction_id == pred_rec.prediction_id

    # 2. Subsequent test execution completes with failure
    subsequent_run = TestRun(
        run_id="run_002",
        application_id="target_eda",
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.MOCK,
        test_case_id="tc_eda_01",
        status=RunStatus.FAILED,
        logs=[],
    )
    repo.create_run(subsequent_run)

    # 3. Evaluate pending predictions
    evaluated = service.evaluate_pending_predictions_for_run(subsequent_run)
    assert len(evaluated) == 1
    assert evaluated[0].evaluation_status == PredictionEvaluationStatus.EVALUATED
    assert evaluated[0].target_run_id == "run_002"
    assert evaluated[0].actual_outcome == 1
    assert evaluated[0].is_correct is True

    # 4. Confirm no pending predictions remaining
    remaining_pending = repo.get_pending_predictions_for_test_case("tc_eda_01")
    assert len(remaining_pending) == 0


# ==========================================
# 7. Scientific Evaluation API Endpoints Tests
# ==========================================

client = TestClient(app)

def test_api_scientific_endpoints():
    # 1. Dataset Audit
    res_audit = client.get("/api/v1/reliability/audit")
    assert res_audit.status_code == 200
    data_audit = res_audit.json()
    assert "status" in data_audit
    assert "total_runs" in data_audit

    # 2. Provenance
    res_prov = client.get("/api/v1/reliability/provenance")
    assert res_prov.status_code == 200
    data_prov = res_prov.json()
    assert isinstance(data_prov, list)

    # 3. Scientific Evaluation Report
    res_eval = client.get("/api/v1/reliability/scientific-evaluation")
    assert res_eval.status_code == 200
    data_eval = res_eval.json()
    assert "dataset_audit" in data_eval
    assert "baselines" in data_eval
    assert "calibration" in data_eval

    # 4. Prediction Records
    res_records = client.get("/api/v1/reliability/prediction-records")
    assert res_records.status_code == 200
    data_records = res_records.json()
    assert isinstance(data_records, list)


# ==========================================
# 8. Small-Data Behavior Tests (Cases A, B, C, D)
# ==========================================

def test_small_data_case_a_no_historical_executions():
    """Case A: Zero historical runs -> NO_DATA status."""
    report = ScientificEvaluator.audit_dataset([])
    assert report.status == DatasetStatus.NO_DATA
    assert report.total_runs == 0
    assert report.total_usable_prediction_samples == 0


def test_small_data_case_b_single_execution():
    """Case B: Only 1 execution -> INSUFFICIENT_DATA status."""
    records = [
        ReliabilityRecord(
            run_id="run_b1",
            target_id="target_b",
            test_case_id="tc_b",
            timestamp="2026-09-24T10:00:00Z",
            run_status="COMPLETED",
            failure_label=0,
        )
    ]
    report = ScientificEvaluator.audit_dataset(records)
    assert report.status == DatasetStatus.INSUFFICIENT_DATA
    assert report.total_usable_prediction_samples == 0


def test_small_data_case_c_repeated_executions_single_class():
    """Case C: Repeated executions but only 1 target outcome class -> INSUFFICIENT_DATA status."""
    records = [
        ReliabilityRecord(
            run_id=f"run_c_{i}",
            target_id="target_c",
            test_case_id="tc_c",
            timestamp=f"2026-09-24T10:0{i}:00Z",
            run_status="COMPLETED",
            failure_label=0,
        )
        for i in range(8)
    ]
    report = ScientificEvaluator.audit_dataset(records)
    assert report.status == DatasetStatus.INSUFFICIENT_DATA
    assert report.positive_labels_count == 0
    assert report.negative_labels_count == 7
    assert "Single-class dataset" in report.status_reason


def test_small_data_case_d_usable_multi_class(sample_records):
    """Case D: Enough repeated executions with both binary outcome classes -> USABLE status."""
    report = ScientificEvaluator.audit_dataset(sample_records)
    assert report.status == DatasetStatus.USABLE
    assert report.total_usable_prediction_samples >= 5
    assert report.positive_labels_count > 0
    assert report.negative_labels_count > 0


# ==========================================
# 9. Mathematical Explainability Tests
# ==========================================

def test_mathematical_explainability_contributions():
    """Verifies that feature contribution is exactly value * weight."""
    model = LogisticReliabilityModel()
    vec = ReliabilityFeatureVector(
        run_id="run_exp_1",
        test_case_id="tc_exp_1",
        target_id="tgt_1",
        timestamp="2026-09-24T12:00:00Z",
        features={
            "recent_fail_rate_3": 0.67,
            "consecutive_fails": 2.0,
            "assertion_failure_count": 1.0,
            "grounding_score": 0.85,
            "regression_detected": 1.0,
        },
    )

    pred = model.predict_test_case(vector=vec, test_case_name="Explainability Test", total_historical_runs=10)
    assert pred.prediction_available is True
    assert len(pred.contributing_features) > 0

    for feat in pred.contributing_features:
        expected_contrib = round(feat.value * feat.weight, 3)
        assert abs(feat.contribution - expected_contrib) < 1e-4

