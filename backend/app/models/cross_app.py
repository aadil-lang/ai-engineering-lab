from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.app.models.enums import CampaignType, ExecutionSource, DatasetStatus
from backend.app.models.reliability import ConfusionMatrix


class MetricStatus(str):
    COMPUTED = "COMPUTED"
    NOT_COMPUTABLE = "NOT_COMPUTABLE"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"


class SafeMetricValue(BaseModel):
    """
    Encapsulates a metric value with explicit validity, uncertainty, and non-computable status.
    Prevents assigning false defaults (e.g. 0.5 AUC) when a metric cannot be mathematically computed.
    """
    metric_name: str
    value: float | None = None
    status: str = "COMPUTED"
    reason: str | None = None
    lower_ci: float | None = None
    upper_ci: float | None = None
    confidence_level: float = 0.95
    is_high_uncertainty: bool = False


class EvaluationDatasetSnapshot(BaseModel):
    """
    Immutable, reproducible snapshot of the frozen evaluation dataset for Slice 6.9.
    """
    snapshot_id: str
    created_at: str
    protocol_version: str = "CrossApplicationEvaluationProtocol v1.0"
    model_version: str = "v1.0-logistic-reliability"
    feature_vector_version: str = "v1.0-temporal"
    feature_schema_version: str = "v1.0"
    population_filter: dict[str, Any]
    application_ids: list[str]
    target_ids: list[str]
    test_case_ids: list[str]
    total_runs: int
    total_transitions: int
    failures_count: int
    passes_count: int
    run_ids: list[str]
    transition_ids: list[str]
    excluded_population_counts: dict[str, int]
    provenance_audit_result: dict[str, Any]


class CrossApplicationEvaluationProtocol(BaseModel):
    """
    Formal specification of CrossApplicationEvaluationProtocol v1.0.
    Frozen protocol ensuring non-negotiable scientific evaluation.
    """
    protocol_id: str = "CrossApplicationEvaluationProtocol-v1.0"
    version: str = "1.0"
    created_at: str
    population: str = "REAL_RELIABILITY and REAL_PLAYWRIGHT"
    feature_version: str = "v1.0-temporal"
    model_version: str = "v1.0-logistic-reliability"
    target_label_definition: str = "Binary failure outcome at t+1 (label_next_failed in {0, 1})"
    training_test_separation: str = "Strict application and temporal isolation; no test-app contamination"
    leakage_invariants: list[str] = [
        "TrainApplications inter TestApplications = empty (LOAO)",
        "prediction_timestamp >= test_feature_timestamp",
        "Feature vector strictly past (up to time t)",
        "fit(train) -> transform(train) -> transform(test); never fit(all_data)",
        "No test-set threshold or hyperparameter tuning",
    ]
    baselines: list[str] = [
        "Majority Class (Mode of training labels)",
        "Historical Prevalence (Training set failure rate)",
        "Last Execution Status (Status of run t)",
        "Historical Failure Frequency (Rolling test case failure frequency)",
    ]
    metrics: list[str] = [
        "Accuracy",
        "Precision",
        "Recall",
        "F1 Score",
        "ROC-AUC (Rank-Sum / Mann-Whitney when both classes present)",
        "Brier Score",
        "Confusion Matrix",
        "Bootstrap 95% Confidence Intervals",
    ]
    minimum_data_requirements: dict[str, int] = {
        "min_train_transitions": 10,
        "min_test_transitions": 5,
        "bootstrap_resamples": 500,
    }


class ModelPerformanceReport(BaseModel):
    """Metrics and sample counts for a single model or baseline."""
    name: str
    sample_count: int
    positive_count: int
    negative_count: int
    predicted_positive_count: int
    predicted_negative_count: int
    accuracy: SafeMetricValue
    precision: SafeMetricValue
    recall: SafeMetricValue
    f1_score: SafeMetricValue
    roc_auc: SafeMetricValue
    brier_score: SafeMetricValue
    confusion_matrix: ConfusionMatrix


class RegimeAResult(BaseModel):
    """Within-Application Temporal Evaluation for a single application."""
    application_id: str
    total_runs: int
    total_transitions: int
    failures_count: int
    passes_count: int
    failure_rate: float
    status: str
    status_reason: str
    train_transitions: int
    test_transitions: int
    num_folds: int
    skipped_folds: int
    model_performance: ModelPerformanceReport | None = None
    baseline_performances: dict[str, ModelPerformanceReport] = {}


class LOAOExperimentResult(BaseModel):
    """Leave-One-Application-Out Experiment Result."""
    experiment_id: str
    train_applications: list[str]
    test_application: str
    train_transitions: int
    train_failures: int
    train_passes: int
    train_failure_rate: float
    test_transitions: int
    test_failures: int
    test_passes: int
    test_failure_rate: float
    leakage_check_passed: bool
    leakage_details: str
    model_performance: ModelPerformanceReport
    baseline_performances: dict[str, ModelPerformanceReport]
    uncertainty_level: str
    uncertainty_notes: list[str]


class RegimeCResult(BaseModel):
    """Combined Cross-Application Temporal Evaluation (Pooled earlier vs later)."""
    regime_id: str = "REGIME_C_COMBINED_TEMPORAL"
    total_transitions: int
    train_transitions: int
    train_failures: int
    train_passes: int
    test_transitions: int
    test_failures: int
    test_passes: int
    split_timestamp: str
    model_performance: ModelPerformanceReport
    baseline_performances: dict[str, ModelPerformanceReport]
    notes: list[str]


class ApplicationConcentrationItem(BaseModel):
    application_id: str
    target_id: str
    runs: int
    transitions: int
    failures: int
    passes: int
    failure_rate: float
    percentage_of_transitions: float


class TestCaseConcentrationItem(BaseModel):
    test_case_id: str
    application_id: str
    runs: int
    transitions: int
    failures: int
    passes: int
    failure_rate: float
    percentage_of_transitions: float


class FeatureDistributionStat(BaseModel):
    feature_name: str
    train_mean: float
    train_std: float
    test_mean: float
    test_std: float
    min_val: float
    max_val: float
    standardized_shift: float
    shift_detected: bool


class FeatureShiftReport(BaseModel):
    experiment_id: str
    train_applications: list[str]
    test_application: str
    features: list[FeatureDistributionStat]


class CrossApplicationEvaluationReport(BaseModel):
    """
    Complete Slice 6.9 Cross-Application Reliability Evaluation Report.
    """
    report_id: str
    created_at: str
    protocol_version: str
    snapshot: EvaluationDatasetSnapshot
    protocol: CrossApplicationEvaluationProtocol
    application_concentration: list[ApplicationConcentrationItem]
    test_case_concentration: list[TestCaseConcentrationItem]
    regime_a_within_application: list[RegimeAResult]
    regime_b_loao: list[LOAOExperimentResult]
    regime_c_combined: RegimeCResult
    feature_distribution_shifts: list[FeatureShiftReport]
    scientific_summary: list[str]
