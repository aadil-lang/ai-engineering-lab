import pytest
import math
from backend.app.models.enums import RunStatus, RunnerType, FailureSource, RiskBand
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilityFeatureVector,
    ClassificationMetrics,
)
from backend.app.prediction.reliability_model import (
    LogisticReliabilityModel,
    ScaledLogisticReliabilityModel,
    WeightedLogisticReliabilityModel,
    BaseBaselinePredictor,
)
from backend.app.prediction.dataset_diagnostics import DatasetDiagnosticsEngine
from backend.app.prediction.scientific_evaluator import ScientificEvaluator
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor


def test_probability_direction_verification():
    """Verifies that predicted probability strictly represents P(next_run_failed = 1)."""
    model = LogisticReliabilityModel("v1.0-test")
    high_risk = {"consecutive_fails": 3.0, "failed_step_count": 2.0, "recent_fail_rate_3": 1.0}
    low_risk = {"consecutive_fails": 0.0, "failed_step_count": 0.0, "recent_fail_rate_3": 0.0}

    prob_high = model.predict_probability(high_risk)
    prob_low = model.predict_probability(low_risk)

    assert prob_high > prob_low, "Higher failure features must produce higher failure probability"
    assert 0.0 <= prob_low <= 1.0
    assert 0.0 <= prob_high <= 1.0

    # Verify decision threshold at 0.50
    pred_high = 1 if prob_high >= 0.50 else 0
    pred_low = 1 if prob_low >= 0.50 else 0
    assert pred_high == 1
    assert pred_low == 0


def test_label_generation_mapping():
    """Verifies that run statuses map deterministically to failure_label (FAILED/ERROR -> 1, PASSED/COMPLETED -> 0)."""
    from backend.app.models.test_run import TestRun

    run_fail = TestRun(run_id="r1", application_id="app1", status=RunStatus.FAILED, started_at="2026-09-24T10:00:00Z")
    rec_fail = ReliabilityFeatureExtractor.extract_record_from_run(run_fail, [], [])
    assert rec_fail.failure_label == 1

    run_err = TestRun(run_id="r2", application_id="app1", status=RunStatus.ERROR, started_at="2026-09-24T10:01:00Z")
    rec_err = ReliabilityFeatureExtractor.extract_record_from_run(run_err, [], [])
    assert rec_err.failure_label == 1

    run_pass = TestRun(run_id="r3", application_id="app1", status=RunStatus.PASSED, started_at="2026-09-24T10:02:00Z")
    rec_pass = ReliabilityFeatureExtractor.extract_record_from_run(run_pass, [], [])
    assert rec_pass.failure_label == 0


def test_prevalence_baseline_and_brier():
    """Verifies prevalence baseline probability and Brier score calculation."""
    train_labels = [1, 1, 0, 0, 0]  # 2/5 = 0.40 prevalence
    p_prev = BaseBaselinePredictor.predict_historical_prevalence(train_labels)
    assert p_prev == 0.40

    test_labels = [1, 0, 0]
    # Brier = 1/3 * ((0.4-1)^2 + (0.4-0)^2 + (0.4-0)^2) = 1/3 * (0.36 + 0.16 + 0.16) = 0.68 / 3 = 0.2267
    brier = sum((p_prev - y) ** 2 for y in test_labels) / len(test_labels)
    assert round(brier, 4) == round(0.68 / 3, 4)


def test_majority_class_baseline():
    """Verifies that majority class baseline strictly predicts the modal training class."""
    assert BaseBaselinePredictor.predict_majority_class([1, 1, 0]) == 1.0
    assert BaseBaselinePredictor.predict_majority_class([0, 0, 1]) == 0.0
    assert BaseBaselinePredictor.predict_majority_class([]) == 0.0


def test_feature_scaling_standard_scaler_train_only():
    """Verifies that StandardScaler is fitted strictly on training data without test leakage."""
    train_vecs = [
        ReliabilityFeatureVector(run_id="r1", target_id="t1", timestamp="2026-09-24T10:00:00Z", features={"duration_ms": 100.0, "consecutive_fails": 0.0}, label_next_failed=0),
        ReliabilityFeatureVector(run_id="r2", target_id="t1", timestamp="2026-09-24T10:01:00Z", features={"duration_ms": 300.0, "consecutive_fails": 2.0}, label_next_failed=1),
    ]
    test_vecs = [
        ReliabilityFeatureVector(run_id="r3", target_id="t1", timestamp="2026-09-24T10:02:00Z", features={"duration_ms": 1000.0, "consecutive_fails": 10.0}, label_next_failed=1),
    ]

    model_v11 = ScaledLogisticReliabilityModel("v1.1-test")
    model_v11.fit_scaler(train_vecs)

    # Train mean of duration_ms should be 200.0, std = 100.0
    assert model_v11.scaler_means["duration_ms"] == 200.0
    assert model_v11.scaler_stds["duration_ms"] == 100.0

    scaled_test = model_v11.transform_features(test_vecs[0].features)
    # (1000 - 200) / 100 = 8.0
    assert scaled_test["duration_ms"] == 8.0


def test_test_case_heterogeneity_and_autocorrelation():
    """Verifies test case transition counting, dominance detection, and lag-1 autocorrelation."""
    records = [
        ReliabilityRecord(run_id=f"r_{i}", target_id="demo", test_case_id="tc_alt", timestamp=f"2026-09-24T10:{i:02d}:00Z", failure_label=i % 2)
        for i in range(10)
    ]
    stats = DatasetDiagnosticsEngine.calculate_test_case_heterogeneity(records)
    assert len(stats) == 1
    assert stats[0].test_case_id == "tc_alt"
    assert stats[0].transition_count == 9
    assert stats[0].autocorrelation_lag1 is not None
    assert stats[0].autocorrelation_lag1 < -0.80  # Perfect alternating sequence has strongly negative autocorrelation


def test_failure_source_classification():
    """Verifies metadata-based failure source classification."""
    records = [
        ReliabilityRecord(run_id="r1", target_id="tgt_demo_shop", runner_type="MOCK", timestamp="2026-09-24T10:00:00Z"),
        ReliabilityRecord(run_id="r2", target_id="app1", test_case_id="tc_ungrounded_123", runner_type="MOCK", timestamp="2026-09-24T10:01:00Z"),
        ReliabilityRecord(run_id="r3", target_id="app1", runner_type="PLAYWRIGHT", timestamp="2026-09-24T10:02:00Z"),
        ReliabilityRecord(run_id="r4", target_id="app1", runner_type="AI_AGENT", timestamp="2026-09-24T10:03:00Z"),
    ]
    sources = DatasetDiagnosticsEngine.classify_failure_sources(records)
    assert sources[FailureSource.DEMO.value] == 1
    assert sources[FailureSource.CONTROLLED_DEFECT.value] == 1
    assert sources[FailureSource.BROWSER.value] == 1
    assert sources[FailureSource.AGENT.value] == 1


def test_known_vs_unseen_distribution_shift():
    """Verifies separation of known vs unseen test cases on the test holdout."""
    train_vecs = [
        ReliabilityFeatureVector(run_id="r1", target_id="t1", test_case_id="tc_alpha", timestamp="2026-09-24T10:00:00Z", label_next_failed=0),
        ReliabilityFeatureVector(run_id="r2", target_id="t1", test_case_id="tc_beta", timestamp="2026-09-24T10:01:00Z", label_next_failed=1),
    ]
    test_vecs = [
        ReliabilityFeatureVector(run_id="r3", target_id="t1", test_case_id="tc_alpha", timestamp="2026-09-24T10:02:00Z", label_next_failed=0),
        ReliabilityFeatureVector(run_id="r4", target_id="t1", test_case_id="tc_gamma", timestamp="2026-09-24T10:03:00Z", label_next_failed=0),
    ]
    report = DatasetDiagnosticsEngine.calculate_distribution_shift(train_vecs, test_vecs)
    assert "tc_alpha" in report.known_test_cases_in_test
    assert "tc_gamma" in report.unseen_test_cases_in_test
    assert report.known_samples_count == 1
    assert report.unseen_samples_count == 1
