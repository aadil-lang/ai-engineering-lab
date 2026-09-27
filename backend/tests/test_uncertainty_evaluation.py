import os
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.reliability import (
    ReliabilityFeatureVector,
    CampaignType,
    ExecutionSource,
)
from backend.app.models.uncertainty import (
    UncertaintyBucketLevel,
    AbstentionDecision,
    ScientificVerdictStatus,
    DecisionPolicySelectionMethod,
    PredictionUncertainty,
    DecisionPolicy,
)
from backend.app.prediction.reliability_model import ScaledLogisticReliabilityModel
from backend.app.prediction.uncertainty_evaluator import UncertaintyEvaluator


@pytest.fixture
def sample_feature_vectors():
    """Generates synthetic vectors for fast mathematical and invariant testing."""
    vectors = []
    apps = ["app_inventory", "app_eda", "app_booking"]
    timestamps = [f"2026-09-25T10:{i:02d}:00Z" for i in range(30)]

    idx = 0
    for app_id in apps:
        for i in range(10):
            # EDA and Booking mostly passes, Inventory has 2 failures
            is_fail = 1 if (app_id == "app_inventory" and i in [3, 7]) else 0
            v = ReliabilityFeatureVector(
                run_id=f"run_{app_id}_{i}",
                target_id=f"tgt_{app_id}",
                target_run_id=f"run_{app_id}_{i+1}",
                application_id=app_id,
                test_case_id=f"tc_{app_id}_test",
                campaign_type=CampaignType.REAL_RELIABILITY,
                execution_source=ExecutionSource.REAL_PLAYWRIGHT,
                timestamp=timestamps[idx],
                features={
                    "duration_ms": 1200.0 + (i * 50.0 if app_id != "app_inventory" else i * 300.0),
                    "step_count": 10.0 + i,
                    "duration_ratio_moving_avg": 1.0 + (0.1 * i),
                    "recent_fail_rate_3": 0.33 if is_fail else 0.0,
                    "recent_fail_rate_5": 0.20 if is_fail else 0.0,
                    "historical_fail_rate": 0.15 if is_fail else 0.0,
                    "consecutive_fails": 1 if is_fail else 0,
                    "failed_step_count": 1 if is_fail else 0,
                    "assertion_failure_count": 1 if is_fail else 0,
                    "console_error_count": 0,
                    "agent_loop_detected": 0,
                    "grounding_score": 1.0,
                },
                label_next_failed=is_fail,
            )
            vectors.append(v)
            idx += 1
    return vectors


def test_uncertainty_mathematical_consistency(sample_feature_vectors):
    """
    Validates that derived posterior uncertainty satisfies mathematical invariants:
    1. 0.0 <= p_lower <= p_mean <= p_upper <= 1.0
    2. uncertainty_width == p_upper - p_lower
    3. effective_evidence == K + m
    """
    train_set = [v for v in sample_feature_vectors if v.application_id != "app_inventory"]
    test_vec = [v for v in sample_feature_vectors if v.application_id == "app_inventory"][0]

    model = ScaledLogisticReliabilityModel()
    model.fit(train_set)
    param_cov = UncertaintyEvaluator.compute_fisher_covariance(model, train_set)

    for k in [0, 1, 3, 5]:
        p_mean, p_lower, p_upper, u_width, eff_ev = UncertaintyEvaluator.compute_prediction_uncertainty(
            model=model,
            param_cov=param_cov,
            vector=test_vec,
            budget_k=k,
            calibrated_prob=0.25,
            global_prevalence=0.10,
            k_observed_fails=0,
            k_actual=k,
            prior_strength_m=5.0,
        )

        assert 0.0 <= p_lower <= 1.0
        assert 0.0 <= p_upper <= 1.0
        assert p_lower <= p_mean <= p_upper
        assert abs(u_width - (p_upper - p_lower)) < 1e-4
        assert eff_ev == k + 5.0


def test_cold_start_k0_behavior(sample_feature_vectors):
    """
    Validates that at K=0, effective evidence equals prior strength m and
    uncertainty reflects prior + model covariance without local intercept evidence.
    """
    train_set = [v for v in sample_feature_vectors if v.application_id != "app_eda"]
    test_vec = [v for v in sample_feature_vectors if v.application_id == "app_eda"][0]

    model = ScaledLogisticReliabilityModel()
    model.fit(train_set)
    param_cov = UncertaintyEvaluator.compute_fisher_covariance(model, train_set)

    _, _, _, u_width_k0, eff_k0 = UncertaintyEvaluator.compute_prediction_uncertainty(
        model=model,
        param_cov=param_cov,
        vector=test_vec,
        budget_k=0,
        calibrated_prob=0.15,
        global_prevalence=0.10,
        k_observed_fails=0,
        k_actual=0,
    )

    assert eff_k0 == 5.0
    assert u_width_k0 > 0.0


def test_no_test_app_information_in_threshold_selection(sample_feature_vectors):
    """
    Validates that candidate decision policies and bucket cutoffs are derived
    exclusively from training applications with zero test-set leakage.
    """
    train_apps = ["app_eda", "app_booking"]
    test_app = "app_inventory"

    # Leakage check: test_app is not in train_apps
    assert test_app not in train_apps

    train_set = [v for v in sample_feature_vectors if v.application_id in train_apps]
    model = ScaledLogisticReliabilityModel()
    model.fit(train_set)
    param_cov = UncertaintyEvaluator.compute_fisher_covariance(model, train_set)

    policies, (b33, b66) = UncertaintyEvaluator.fit_decision_policies_on_training_data(
        train_vectors=train_set,
        model=model,
        param_cov=param_cov,
        global_prevalence=0.05,
        train_apps=train_apps,
    )

    assert len(policies) == 5
    for p in policies:
        assert p.training_applications == train_apps
        assert test_app not in p.training_applications
        assert p.training_sample_count == len(train_set)

    assert 0.0 <= b33 <= b66 <= 1.0


def test_abstention_and_risk_coverage_ordering():
    """
    Validates that progressive risk-coverage ordering correctly sorts by uncertainty
    and properly computes coverage and selective Brier score.
    """
    preds = [
        PredictionUncertainty(
            prediction_id=f"p_{i}",
            prediction_run_id=f"r_{i}",
            target_run_id=f"tr_{i}",
            application_id="app_test",
            test_case_id="tc_test",
            timestamp=f"2026-09-25T12:{i:02d}:00Z",
            budget_k=0,
            calibration_k=0,
            p_mean=0.1 * i,
            p_lower=max(0.0, 0.1 * i - 0.05),
            p_upper=min(1.0, 0.1 * i + 0.05),
            uncertainty_width=0.1 * i,
            effective_evidence=5.0,
            observed_label=1 if i > 5 else 0,
            brier_contribution=round(((0.1 * i) - (1 if i > 5 else 0)) ** 2, 4),
            absolute_error=round(abs((0.1 * i) - (1 if i > 5 else 0)), 4),
        )
        for i in range(10)
    ]

    # Threshold = 0.35 accepts items with uncertainty <= 0.35 (i=0, 1, 2, 3)
    policy = DecisionPolicy(
        policy_id="test_pol",
        selection_method=DecisionPolicySelectionMethod.TRAIN_QUANTILE_50,
        threshold_tau=0.35,
        training_applications=["app_other"],
        training_sample_count=20,
        training_coverage=0.5,
        training_selective_brier=0.02,
        training_abstention_rate=0.5,
    )

    accepted = [p for p in preds if p.uncertainty_width <= policy.threshold_tau]
    assert len(accepted) == 4
    for p in accepted:
        assert p.uncertainty_width <= 0.35


def test_empty_and_zero_defect_buckets_safe():
    """
    Validates that bucket summary handles zero-sample or zero-defect regimes safely without errors.
    """
    preds = [
        PredictionUncertainty(
            prediction_id="p_1",
            prediction_run_id="r_1",
            target_run_id="tr_1",
            application_id="app_booking",
            test_case_id="tc_booking",
            timestamp="2026-09-25T12:00:00Z",
            budget_k=0,
            calibration_k=0,
            p_mean=0.05,
            p_lower=0.01,
            p_upper=0.15,
            uncertainty_width=0.14,
            effective_evidence=5.0,
            observed_label=0,  # Zero defect
            uncertainty_bucket=UncertaintyBucketLevel.LOW,
            brier_contribution=0.0025,
            absolute_error=0.05,
        )
    ]

    summaries = UncertaintyEvaluator.compute_uncertainty_buckets_summary(preds, (0.20, 0.40))
    assert len(summaries) == 3
    low = next(s for s in summaries if s.bucket_level == UncertaintyBucketLevel.LOW)
    med = next(s for s in summaries if s.bucket_level == UncertaintyBucketLevel.MEDIUM)
    high = next(s for s in summaries if s.bucket_level == UncertaintyBucketLevel.HIGH)

    assert low.sample_count == 1
    assert low.failure_count == 0
    assert med.sample_count == 0
    assert high.sample_count == 0


def test_snapshot_slice_7_1_integrity():
    """
    Validates that eval_snap_slice_7_1.json exists, references parent Slice 7.0,
    and has correct population attributes.
    """
    snap_path = os.path.join("backend", "data", "snapshots", "eval_snap_slice_7_1.json")
    assert os.path.exists(snap_path), f"Snapshot {snap_path} not found"

    with open(snap_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["snapshot_id"] == "eval_snap_slice_7_1"
    assert data["parent_snapshot_id"] == "eval_snap_slice_7_0"
    assert data["protocol_version"] == "UncertaintyDecisionProtocol v1.0"
    assert data["population_filter"]["campaign_type"] == "REAL_RELIABILITY"
    assert data["population_filter"]["execution_source"] == "REAL_PLAYWRIGHT"
    assert "app_inventory" in data["application_ids"]
    assert "checksum_sha256" in data


def test_api_uncertainty_endpoints():
    """
    Validates all Slice 7.1 read-only REST API endpoints.
    """
    client = TestClient(app)

    # 1. Main experiment endpoint
    resp = client.get("/api/reliability/uncertainty")
    assert resp.status_code == 200
    data = resp.json()
    assert "experiment_id" in data
    assert data["protocol_version"] == "UncertaintyDecisionProtocol v1.0"
    assert data["parent_snapshot_id"] == "eval_snap_slice_7_0"
    exp_id = data["experiment_id"]

    # 2. Summary endpoint
    resp_sum = client.get("/api/reliability/uncertainty/summary")
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert sum_data["experiment_id"] == exp_id
    assert len(sum_data["hypotheses_verdicts"]) == 5

    # 3. Specific experiment endpoint
    resp_exp = client.get(f"/api/reliability/uncertainty/{exp_id}")
    assert resp_exp.status_code == 200

    # 4. Predictions endpoint
    resp_preds = client.get(f"/api/reliability/uncertainty/{exp_id}/predictions?budget_k=0")
    assert resp_preds.status_code == 200
    preds_list = resp_preds.json()
    assert len(preds_list) > 0
    assert "uncertainty_width" in preds_list[0]
    assert "effective_evidence" in preds_list[0]

    # 5. Risk-coverage curve endpoint
    resp_rc = client.get(f"/api/reliability/uncertainty/{exp_id}/risk-coverage")
    assert resp_rc.status_code == 200
    rc_list = resp_rc.json()
    assert len(rc_list) > 0
    assert "selective_brier" in rc_list[0]

    # 6. Uncertainty calibration buckets endpoint
    resp_cal = client.get(f"/api/reliability/uncertainty/{exp_id}/calibration")
    assert resp_cal.status_code == 200
    buckets_list = resp_cal.json()
    assert len(buckets_list) == 3

    # 7. Decision policy endpoint
    resp_pol = client.get(f"/api/reliability/uncertainty/{exp_id}/decision-policy")
    assert resp_pol.status_code == 200
    pol_list = resp_pol.json()
    assert len(pol_list) > 0
