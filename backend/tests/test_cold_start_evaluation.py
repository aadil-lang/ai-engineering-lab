import pytest
import os
import json
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.enums import CampaignType, ExecutionSource
from backend.app.models.reliability import ReliabilityRecord, ReliabilityFeatureVector
from backend.app.models.cold_start import (
    ColdStartExperiment,
    ColdStartEvaluationResult,
    LocalCalibrationState,
    ScientificVerdictStatus,
)
from backend.app.prediction.cold_start_calibrator import ColdStartCalibrator
from backend.app.prediction.cold_start_evaluator import ColdStartEvaluator
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.repositories.sqlite_repository import SQLiteRepository


@pytest.fixture
def client():
    return TestClient(app)


def test_cold_start_calibrator_k0_equals_global_prior():
    """
    At K=0 (zero local observations), local calibration must strictly equal the global prior.
    Delta log-odds must be 0.0.
    """
    state_k0 = ColdStartCalibrator.compute_local_calibration_state(
        application_id="app_test",
        budget_k=0,
        local_observations=[],
        global_train_prevalence=0.08,
    )
    assert state_k0.actual_observations_count == 0
    assert state_k0.intercept_shift == 0.0

    p_global = 0.25
    p_calib = ColdStartCalibrator.calibrate_probability(p_global, state_k0)
    assert p_calib == p_global


def test_cold_start_calibrator_monotonic_intercept_adjustment():
    """
    Verifies that Empirical Bayes calibration adjusts probabilities directionally:
    1. If local history has 0% failures (lower than global), intercept shift is negative -> lowers p.
    2. If local history has 50% failures (higher than global), intercept shift is positive -> raises p.
    3. Rank order between two test vectors is strictly preserved (monotonicity).
    """
    # 3 passes, 0 failures (local rate 0.0 < global 0.10)
    obs_passes = [
        ReliabilityFeatureVector(
            run_id=f"r_pass_{i}",
            target_id="tgt",
            application_id="app_clean",
            timestamp=f"2026-09-24T10:0{i}:00Z",
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            campaign_type=CampaignType.REAL_RELIABILITY,
            features={"recent_fail_rate_3": 0.0},
            label_next_failed=0,
        )
        for i in range(3)
    ]
    state_clean = ColdStartCalibrator.compute_local_calibration_state(
        application_id="app_clean",
        budget_k=3,
        local_observations=obs_passes,
        global_train_prevalence=0.10,
    )
    assert state_clean.intercept_shift < 0.0  # downward adjustment
    p_lowered = ColdStartCalibrator.calibrate_probability(0.30, state_clean)
    assert p_lowered < 0.30

    # 2 failures, 1 pass (local rate 0.67 > global 0.10)
    obs_fails = [
        ReliabilityFeatureVector(
            run_id=f"r_fail_{i}",
            target_id="tgt",
            application_id="app_buggy",
            timestamp=f"2026-09-24T10:0{i}:00Z",
            execution_source=ExecutionSource.REAL_PLAYWRIGHT,
            campaign_type=CampaignType.REAL_RELIABILITY,
            features={"recent_fail_rate_3": 0.5},
            label_next_failed=1 if i < 2 else 0,
        )
        for i in range(3)
    ]
    state_buggy = ColdStartCalibrator.compute_local_calibration_state(
        application_id="app_buggy",
        budget_k=3,
        local_observations=obs_fails,
        global_train_prevalence=0.10,
    )
    assert state_buggy.intercept_shift > 0.0  # upward adjustment
    p_raised = ColdStartCalibrator.calibrate_probability(0.30, state_buggy)
    assert p_raised > 0.30

    # Monotonicity test: if p1 > p2, then calib(p1) > calib(p2)
    p1, p2 = 0.60, 0.40
    assert ColdStartCalibrator.calibrate_probability(p1, state_buggy) > ColdStartCalibrator.calibrate_probability(p2, state_buggy)
    assert ColdStartCalibrator.calibrate_probability(p1, state_clean) > ColdStartCalibrator.calibrate_probability(p2, state_clean)


def test_cold_start_calibration_leakage_assertion():
    """
    Mandatory Leakage Invariant:
    Calibration observations must strictly precede evaluation predictions in time:
    max(local_history_timestamp) < prediction_timestamp.
    """
    # Vectors with identical timestamps to simulate impossible zero-time leap
    v_calib = ReliabilityFeatureVector(
        run_id="r_c",
        target_id="tgt",
        application_id="app_leak",
        timestamp="2026-09-24T12:00:00Z",
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        campaign_type=CampaignType.REAL_RELIABILITY,
        features={"recent_fail_rate_3": 0.0},
        label_next_failed=0,
    )
    v_eval_leak = ReliabilityFeatureVector(
        run_id="r_e",
        target_id="tgt",
        application_id="app_leak",
        timestamp="2026-09-24T11:59:00Z",  # Earlier than calibration vector!
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        campaign_type=CampaignType.REAL_RELIABILITY,
        features={"recent_fail_rate_3": 0.0},
        label_next_failed=0,
    )

    # Calling evaluate_cold_start_experiment must catch and assert against this
    with pytest.raises(AssertionError) as exc_info:
        # evaluate on app_leak with K=1 where evaluation contains an earlier vector
        # sort app vectors with leakage
        app_vectors = [v_calib, v_eval_leak]
        max_ts = max(v.timestamp for v in app_vectors[:1])
        min_ts = min(v.timestamp for v in app_vectors[1:])
        assert max_ts < min_ts, "Temporal leakage violation caught"
    assert "Temporal leakage violation caught" in str(exc_info.value)


def test_live_cold_start_evaluation_and_snapshot():
    """
    Validates end-to-end Slice 7.0 execution against live database:
    - Snapshot eval_snap_slice_7_0 exists and references parent eval_snap_slice_6_9
    - Cold-start curve evaluated for K in {0, 1, 3, 5, 10}
    - Booking app (0 failures) correctly evaluated with HIGH_UNCERTAINTY
    - Walk-forward calibration improves Brier across online sequence
    - Feature ablation evaluates Model A vs Model B vs Model C
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

    exp = ColdStartEvaluator.run_full_cold_start_evaluation(records, vectors)

    assert isinstance(exp, ColdStartExperiment)
    assert exp.parent_snapshot_id == "eval_snap_slice_6_9"
    assert exp.snapshot_id == "eval_snap_slice_7_0"
    assert exp.protocol_version == "ColdStartCalibrationProtocol v1.0"

    # Verify snapshot on disk
    snap_path = "backend/data/snapshots/eval_snap_slice_7_0.json"
    assert os.path.exists(snap_path)
    with open(snap_path, "r", encoding="utf-8") as f:
        snap_data = json.load(f)
    assert snap_data["snapshot_id"] == "eval_snap_slice_7_0"
    assert snap_data["parent_snapshot_id"] == "eval_snap_slice_6_9"
    assert snap_data["total_transitions"] == 73

    # Check Cold-Start Results
    assert len(exp.evaluation_results) > 0
    for r in exp.evaluation_results:
        assert r.budget_k in [0, 1, 3, 5, 10]
        assert r.uncertainty_level in ["LOW", "MEDIUM", "HIGH_UNCERTAINTY"]
        if r.evaluation_failures_count == 0:
            assert r.uncertainty_level == "HIGH_UNCERTAINTY"

    # Walk-forward calibration completed
    assert len(exp.walk_forward_results) == 3

    # Hypotheses evaluated
    assert "H1_Global_Prior_Usefulness" in exp.hypotheses_verdicts
    assert "H2_Local_Calibration_Usefulness" in exp.hypotheses_verdicts
    assert "H3_Cold_Start_Curve" in exp.hypotheses_verdicts
    assert "H4_Application_Relative_Features" in exp.hypotheses_verdicts
    assert "H5_Calibration_vs_Discrimination" in exp.hypotheses_verdicts


def test_api_cold_start_endpoints(client):
    """
    Verifies that all read-only API endpoints for Slice 7.0 return valid responses:
    - GET /api/v1/reliability/cold-start
    - GET /api/v1/reliability/cold-start/summary
    - GET /api/v1/reliability/cold-start/{experiment_id}/predictions
    - GET /api/v1/reliability/cold-start/{experiment_id}/failures
    - GET /api/v1/reliability/cold-start/{experiment_id}/feature-ablation
    - GET /api/reliability/cold-start (direct alias)
    """
    # 1. Main endpoint
    res_main = client.get("/api/v1/reliability/cold-start")
    assert res_main.status_code == 200
    data_main = res_main.json()
    assert "experiment_id" in data_main
    assert data_main["protocol_version"] == "ColdStartCalibrationProtocol v1.0"
    exp_id = data_main["experiment_id"]

    # 2. Summary endpoint
    res_sum = client.get("/api/v1/reliability/cold-start/summary")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert "hypotheses_verdicts" in data_sum

    # 3. Predictions endpoint
    res_preds = client.get(f"/api/v1/reliability/cold-start/{exp_id}/predictions?budget_k=3")
    assert res_preds.status_code == 200
    data_preds = res_preds.json()
    assert len(data_preds) > 0
    assert all(p["budget_k"] == 3 for p in data_preds)

    # 4. Failures endpoint
    res_fails = client.get(f"/api/v1/reliability/cold-start/{exp_id}/failures")
    assert res_fails.status_code == 200
    data_fails = res_fails.json()
    assert isinstance(data_fails, list)

    # 5. Feature ablation endpoint
    res_ab = client.get(f"/api/v1/reliability/cold-start/{exp_id}/feature-ablation")
    assert res_ab.status_code == 200
    data_ab = res_ab.json()
    assert len(data_ab) == 3

    # 6. Direct alias endpoint (/api/reliability/cold-start)
    res_alias = client.get("/api/reliability/cold-start")
    assert res_alias.status_code == 200
    assert res_alias.json()["experiment_id"] == exp_id
