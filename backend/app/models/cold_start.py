from typing import Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.app.models.enums import CampaignType, ExecutionSource
from backend.app.models.reliability import ConfusionMatrix
from backend.app.models.cross_app import SafeMetricValue, ModelPerformanceReport


class ScientificVerdictStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FeatureCategory(str, Enum):
    RAW_APPLICATION_DEPENDENT = "RAW_APPLICATION_DEPENDENT"
    APPLICATION_RELATIVE = "APPLICATION_RELATIVE"
    TEMPORAL = "TEMPORAL"
    FAILURE_HISTORY = "FAILURE_HISTORY"
    AGENT_BEHAVIOR = "AGENT_BEHAVIOR"


class CalibrationObservation(BaseModel):
    """A single local historical observation used for calibration."""
    run_id: str
    target_run_id: str | None = None
    timestamp: str
    outcome: int
    duration_ms: float
    failed_step_count: int


class LocalCalibrationState(BaseModel):
    """Summary of local application history available up to cutoff K."""
    application_id: str
    budget_k: int
    actual_observations_count: int
    cutoff_timestamp: str
    observed_failures: int
    observed_passes: int
    empirical_failure_rate: float
    shrunk_failure_rate: float
    intercept_shift: float
    observation_run_ids: list[str]


class ColdStartPrediction(BaseModel):
    """Audit-trailed prediction for a single test transition under a cold-start regime."""
    prediction_id: str
    experiment_id: str
    held_out_application_id: str
    budget_k: int
    run_id: str
    target_run_id: str
    feature_timestamp: str
    prediction_timestamp: str
    local_history_cutoff_timestamp: str
    local_history_count: int
    local_history_run_ids: list[str]
    global_probability: float
    local_baseline_probability: float
    calibrated_probability: float
    observed_label: int
    global_predicted_class: int
    calibrated_predicted_class: int
    calibration_method: str = "empirical_bayes_log_odds"
    is_leakage_free: bool = True


class OperationalMetrics(BaseModel):
    """Operational reliability QA metrics."""
    failures_detected: int
    failures_missed: int
    false_alarms: int
    total_eval_samples: int
    fraction_selected_for_qa: float  # proportion with predicted prob >= threshold
    qa_workload_reduction_pct: float  # proportion of test runs safely bypassed without missing failures


class ColdStartEvaluationResult(BaseModel):
    """Evaluation metrics for a specific (Held-Out App, Budget K, Strategy) configuration."""
    result_id: str
    held_out_application_id: str
    budget_k: int
    evaluation_sample_count: int
    evaluation_failures_count: int
    evaluation_passes_count: int
    evaluation_failure_rate: float
    strategy_a_global: ModelPerformanceReport
    strategy_b_local: ModelPerformanceReport
    strategy_c_calibrated: ModelPerformanceReport
    delta_brier_calib_vs_global: float  # calibrated_brier - global_brier (negative is improvement)
    delta_auc_calib_vs_global: float | None = None
    delta_accuracy_calib_vs_global: float
    delta_brier_calib_vs_local: float
    delta_auc_calib_vs_local: float | None = None
    operational_metrics_global: OperationalMetrics
    operational_metrics_calibrated: OperationalMetrics
    uncertainty_level: str  # LOW, MEDIUM, HIGH_UNCERTAINTY
    uncertainty_reasons: list[str]


class WalkForwardStepResult(BaseModel):
    """Single step in an online walk-forward calibration sequence."""
    step_index: int
    run_id: str
    target_run_id: str
    timestamp: str
    cumulative_local_observations: int
    observed_label: int
    global_prob: float
    local_prob: float
    calibrated_prob: float
    calibrated_prediction: int


class WalkForwardColdStartResult(BaseModel):
    """Results of continuous walk-forward online calibration on held-out application."""
    held_out_application_id: str
    min_initial_observations: int
    total_steps: int
    failures_observed: int
    passes_observed: int
    steps: list[WalkForwardStepResult]
    global_metrics: ModelPerformanceReport
    local_metrics: ModelPerformanceReport
    calibrated_metrics: ModelPerformanceReport


class ColdStartFailureAnalysis(BaseModel):
    """Inspection record for an individual failure under cold-start calibration."""
    failure_id: str
    run_id: str
    target_run_id: str
    application_id: str
    test_case_id: str
    failure_timestamp: str
    feature_timestamp: str
    observed_label: int = 1
    global_prob: float
    calibrated_prob: float
    classification_outcome_global: str  # TRUE_POSITIVE, FALSE_NEGATIVE
    classification_outcome_calibrated: str  # TRUE_POSITIVE, FALSE_NEGATIVE
    preceding_duration_ratio: float
    preceding_console_errors: int
    preceding_failed_steps: int
    preceding_consecutive_fails: int
    preceding_telemetry_deterioration_detected: bool
    explanation: str


class FeatureAblationModelResult(BaseModel):
    """Results for one feature ablation model variant."""
    model_name: str
    feature_count: int
    features_used: list[str]
    accuracy: float
    brier_score: float
    roc_auc: float | None = None
    roc_auc_status: str


class FeatureAblationExperimentResult(BaseModel):
    """Secondary analysis comparing Model A (All), Model B (No absolute), Model C (Relative only)."""
    held_out_application_id: str
    budget_k: int
    model_a_all_features: FeatureAblationModelResult
    model_b_no_absolute_features: FeatureAblationModelResult
    model_c_relative_only_features: FeatureAblationModelResult
    conclusion: str


class ApplicationShiftItem(BaseModel):
    """Feature shift for a single feature under cross-application holdout."""
    feature_name: str
    category: str
    train_mean: float
    train_std: float
    test_mean: float
    test_std: float
    standardized_shift: float
    shift_detected: bool


class ApplicationShiftReport(BaseModel):
    held_out_application_id: str
    train_applications: list[str]
    shifts: list[ApplicationShiftItem]
    raw_feature_avg_shift: float
    relative_feature_avg_shift: float
    summary: str


class ColdStartExperiment(BaseModel):
    """Top-level record of a full Slice 7.0 cold-start calibration experiment."""
    experiment_id: str
    created_at: str
    protocol_version: str = "ColdStartCalibrationProtocol v1.0"
    parent_snapshot_id: str = "eval_snap_slice_6_9"
    snapshot_id: str = "eval_snap_slice_7_0"
    model_version: str = "v1.1-scaled-logistic"
    feature_vector_version: str = "v1.0-temporal"
    calibration_method: str = "empirical_bayes_log_odds"
    applications_evaluated: list[str]
    budget_k_values: list[int]
    evaluation_results: list[ColdStartEvaluationResult]
    walk_forward_results: list[WalkForwardColdStartResult]
    failure_analyses: list[ColdStartFailureAnalysis]
    feature_ablation_results: list[FeatureAblationExperimentResult]
    shift_reports: list[ApplicationShiftReport]
    hypotheses_verdicts: dict[str, str]  # H1..H5 -> VerdictStatus
    scientific_summary: list[str]
