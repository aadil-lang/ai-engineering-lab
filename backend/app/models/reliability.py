from typing import Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import (
    TrendStatus,
    RiskBand,
    PredictionStatus,
    FailureCategory,
    ExecutionSource,
    PopulationType,
    CampaignType,
)

class ReliabilityRecord(BaseModel):
    """
    Structured historical reliability record derived deterministically from actual QA platform telemetry.
    Traceable to a specific historical run without fabrication.
    """
    record_id: str = Field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    run_id: str
    target_id: str
    application_id: str | None = None
    application_type: str | None = None
    campaign_id: str | None = None
    campaign_type: CampaignType | None = None
    test_case_id: str | None = None
    timestamp: str
    runner_type: str = "MOCK"
    run_status: str = "COMPLETED"
    execution_source: ExecutionSource = ExecutionSource.UNKNOWN
    duration_ms: int = 0
    step_count: int = 0
    failed_step_count: int = 0
    assertion_failure_count: int = 0
    console_error_count: int = 0
    network_error_count: int = 0
    http_4xx_count: int = 0
    http_5xx_count: int = 0
    navigation_failure_count: int = 0
    browser_error_count: int = 0
    agent_loop_detected: bool = False
    grounding_score: float = 1.0
    unsupported_claim_count: int = 0
    contradicted_claim_count: int = 0
    remediation_attempts: int = 0
    remediation_status: str | None = None
    regression_detected: bool = False
    failure_label: int = 0  # 1 for FAILED/ERROR, 0 for PASSED

class ReliabilityFeatureVector(BaseModel):
    """
    Extracted feature vector for sequence modeling and predictive QA.
    """
    run_id: str
    test_case_id: str | None = None
    target_id: str
    application_id: str | None = None
    application_type: str | None = None
    campaign_id: str | None = None
    campaign_type: CampaignType | None = None
    timestamp: str
    execution_source: ExecutionSource = ExecutionSource.UNKNOWN
    features: dict[str, float] = Field(default_factory=dict)
    label_next_failed: int | None = None  # Supervised temporal target (next run failed)
    target_run_id: str | None = None
    target_execution_source: ExecutionSource | None = None
    target_campaign_type: CampaignType | None = None




class FeatureImportance(BaseModel):
    feature_name: str
    weight: float
    value: float
    contribution: float
    description: str

class TestCasePrediction(BaseModel):
    test_case_id: str
    test_case_name: str | None = None
    target_id: str
    prediction_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    failure_probability: float | None = None
    risk_band: RiskBand = RiskBand.UNKNOWN
    status: PredictionStatus = PredictionStatus.INSUFFICIENT_DATA
    model_version: str = "v1.0-logistic-baseline"
    feature_snapshot: dict[str, float] = Field(default_factory=dict)
    training_data_size: int = 0
    prediction_available: bool = False
    contributing_features: list[FeatureImportance] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    baseline_probabilities: dict[str, float] = Field(default_factory=dict)

class ReliabilitySummary(BaseModel):
    total_runs: int
    total_failures: int
    failure_rate: float
    successful_remediation_rate: float
    regression_rate: float
    avg_remediation_attempts: float
    avg_execution_duration_ms: float
    prediction_coverage_pct: float
    active_targets_count: int
    active_test_cases_count: int
    overall_trend: TrendStatus

class TargetReliability(BaseModel):
    target_id: str
    target_name: str
    run_count: int
    failure_count: int
    failure_rate: float
    recent_trend: TrendStatus
    grounded_component_failures: dict[str, int] = Field(default_factory=dict)

class TestCaseReliability(BaseModel):
    test_case_id: str
    test_case_name: str
    target_id: str
    execution_count: int
    failure_count: int
    failure_rate: float
    recent_trend: TrendStatus
    last_run_status: str | None = None
    last_run_timestamp: str | None = None
    prediction: TestCasePrediction | None = None

class FailurePattern(BaseModel):
    category: str
    count: int
    percentage: float
    avg_duration_ms: float
    top_grounded_components: list[str] = Field(default_factory=list)

class TrendPoint(BaseModel):
    time_bucket: str
    total_runs: int
    failed_runs: int
    failure_rate: float

class TrendAnalysis(BaseModel):
    overall_trend: TrendStatus
    historical_failure_rate: float
    recent_failure_rate: float
    data_points: list[TrendPoint] = Field(default_factory=list)
    trend_description: str = ""

from backend.app.models.enums import (
    TrendStatus,
    RiskBand,
    PredictionStatus,
    FailureCategory,
    DatasetStatus,
    PredictionEvaluationStatus,
    EvaluationSplitType,
)

class ConfusionMatrix(BaseModel):
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

class ClassificationMetrics(BaseModel):
    sample_count: int = 0
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    confusion_matrix: ConfusionMatrix = Field(default_factory=ConfusionMatrix)
    notes: list[str] = Field(default_factory=list)

class DatasetAuditReport(BaseModel):
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    passed_runs: int = 0
    total_test_cases: int = 0
    runs_with_repeated_executions: int = 0
    total_usable_reliability_records: int = 0
    total_usable_prediction_samples: int = 0  # t -> t+1 transitions
    positive_labels_count: int = 0  # next_run_failed = 1
    negative_labels_count: int = 0  # next_run_failed = 0
    unique_test_cases_count: int = 0
    earliest_execution_timestamp: str | None = None
    latest_execution_timestamp: str | None = None
    samples_per_test_case: dict[str, int] = Field(default_factory=dict)
    single_execution_test_cases_count: int = 0
    repeated_execution_test_cases_count: int = 0
    status: DatasetStatus = DatasetStatus.NO_DATA
    status_reason: str = ""

class DatasetProvenanceRecord(BaseModel):
    sample_id: str
    test_case_id: str
    feature_run_id: str
    target_run_id: str
    feature_timestamp: str
    target_timestamp: str
    execution_source: ExecutionSource = ExecutionSource.UNKNOWN
    feature_vector_version: str = "v1.0-temporal"
    feature_names: list[str] = Field(default_factory=list)
    target_label: int  # 1 for FAILED, 0 for PASSED


class SplitEvaluationMetrics(BaseModel):
    split_name: EvaluationSplitType
    sample_count: int
    time_range_start: str | None = None
    time_range_end: str | None = None
    positive_count: int = 0
    negative_count: int = 0
    metrics: ClassificationMetrics = Field(default_factory=ClassificationMetrics)

class BaselineEvaluation(BaseModel):
    baseline_id: str
    baseline_name: str
    description: str
    metrics: ClassificationMetrics = Field(default_factory=ClassificationMetrics)

class CalibrationMetrics(BaseModel):
    is_evaluated: bool = False
    brier_score: float | None = None
    expected_calibration_error: float | None = None
    reliability_diagram_bins: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "INSUFFICIENT_DATA"
    notes: list[str] = Field(default_factory=list)

class PredictionRecord(BaseModel):
    prediction_id: str = Field(default_factory=lambda: f"pred_{uuid.uuid4().hex[:8]}")
    test_case_id: str
    test_case_name: str | None = None
    feature_run_id: str
    predicted_failure_probability: float | None = None
    predicted_risk_band: RiskBand = RiskBand.UNKNOWN
    prediction_class: int = 0  # 1 if prob >= 0.5 else 0
    model_version: str = "v1.0-logistic-reliability"
    feature_vector_version: str = "v1.0-temporal"
    prediction_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    target_run_id: str | None = None
    actual_outcome: int | None = None  # 1 for FAILED, 0 for PASSED
    is_correct: bool | None = None
    evaluation_status: PredictionEvaluationStatus = PredictionEvaluationStatus.PENDING
    evaluated_at: str | None = None

class ModelEvaluationMetrics(BaseModel):
    model_version: str
    trained_at: str
    train_samples: int
    test_samples: int
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    brier_score: float | None = None
    baseline_accuracies: dict[str, float] = Field(default_factory=dict)
    is_calibrated: bool = False
    status: PredictionStatus = PredictionStatus.INSUFFICIENT_DATA
    notes: list[str] = Field(default_factory=list)

class QAPrioritizationItem(BaseModel):
    priority_rank: int
    test_case_id: str
    test_case_name: str
    target_id: str
    risk_band: RiskBand
    failure_probability: float | None = None
    trend: TrendStatus
    reason: str

class ContinuousScientificEvaluationReport(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dataset_audit: DatasetAuditReport
    provenance_samples: list[DatasetProvenanceRecord] = Field(default_factory=list)
    splits: list[SplitEvaluationMetrics] = Field(default_factory=list)
    baselines: list[BaselineEvaluation] = Field(default_factory=list)
    model_evaluation: SplitEvaluationMetrics | None = None
    calibration: CalibrationMetrics = Field(default_factory=CalibrationMetrics)
    evaluated_predictions_count: int = 0
    pending_predictions_count: int = 0
    prediction_records: list[PredictionRecord] = Field(default_factory=list)
    evaluation_summary_notes: list[str] = Field(default_factory=list)

class FeatureDistributionStat(BaseModel):
    feature_name: str
    train_mean: float
    train_std: float
    train_min: float
    train_max: float
    test_mean: float
    test_std: float
    test_min: float
    test_max: float
    is_constant: bool = False
    is_near_constant: bool = False
    distribution_shift: str = "STABLE"

class FeaturePredictivenessStat(BaseModel):
    feature_name: str
    training_correlation: float | None = None
    association_description: str
    is_statistically_informative: bool = False

class TestCaseHeterogeneityStat(BaseModel):
    test_case_id: str
    total_executions: int
    transition_count: int
    failures_count: int
    passes_count: int
    failure_rate: float
    dominant_runner: str
    autocorrelation_lag1: float | None = None
    is_dominant: bool = False

class SequenceAnalysisReport(BaseModel):
    sequence_name: str
    total_runs: int
    failures: int
    passes: int
    failure_rate: float
    transition_counts: dict[str, int] = Field(default_factory=dict)
    autocorrelation_lag1: float | None = None
    is_alternating_harness_pattern: bool = False
    description: str = ""

class TestDistributionShiftReport(BaseModel):
    train_test_case_count: int
    test_test_case_count: int
    known_test_cases_in_test: list[str] = Field(default_factory=list)
    unseen_test_cases_in_test: list[str] = Field(default_factory=list)
    known_samples_count: int
    unseen_samples_count: int
    known_accuracy: float | None = None
    unseen_accuracy: float | None = None
    known_metrics: ClassificationMetrics | None = None
    unseen_metrics: ClassificationMetrics | None = None

class ModelComparisonItem(BaseModel):
    model_id: str
    model_name: str
    version: str
    description: str
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    brier_score: float | None = None
    confusion_matrix: ConfusionMatrix = Field(default_factory=ConfusionMatrix)

class DatasetDiagnosticsReport(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_runs: int = 0
    total_transitions: int = 0
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    class_balance: dict[str, Any] = Field(default_factory=dict)
    brier_interpretation: dict[str, Any] = Field(default_factory=dict)
    feature_distributions: list[FeatureDistributionStat] = Field(default_factory=list)
    feature_predictiveness: list[FeaturePredictivenessStat] = Field(default_factory=list)
    test_case_heterogeneity: list[TestCaseHeterogeneityStat] = Field(default_factory=list)
    demo_shop_analysis: SequenceAnalysisReport | None = None
    distribution_shift: TestDistributionShiftReport
    failure_sources: dict[str, int] = Field(default_factory=dict)
    model_comparisons: list[ModelComparisonItem] = Field(default_factory=list)
    data_quality_warnings: list[str] = Field(default_factory=list)
    root_diagnostic_findings: list[str] = Field(default_factory=list)
    recommended_next_experiment: list[str] = Field(default_factory=list)

class PopulationAuditSummary(BaseModel):

    population_id: PopulationType
    population_name: str
    description: str
    total_runs: int = 0
    total_transitions: int = 0
    failures_count: int = 0
    passes_count: int = 0
    failure_rate: float = 0.0
    status: DatasetStatus = DatasetStatus.NO_DATA
    status_reason: str = ""
    included_sources: list[ExecutionSource] = Field(default_factory=list)

class WalkForwardFoldMetric(BaseModel):
    fold_index: int
    train_start_timestamp: str | None = None
    train_end_timestamp: str | None = None
    test_start_timestamp: str | None = None
    test_end_timestamp: str | None = None
    train_sample_count: int = 0
    test_sample_count: int = 0
    train_failure_rate: float = 0.0
    test_failure_rate: float = 0.0
    model_metrics: dict[str, ClassificationMetrics] = Field(default_factory=dict)
    brier_scores: dict[str, float] = Field(default_factory=dict)

class WalkForwardModelAggregate(BaseModel):
    model_id: str
    model_name: str
    mean_accuracy: float | None = None
    std_accuracy: float | None = None
    mean_brier_score: float | None = None
    std_brier_score: float | None = None
    mean_roc_auc: float | None = None
    std_roc_auc: float | None = None
    mean_f1: float | None = None
    std_f1: float | None = None
    mean_ece: float | None = None
    std_ece: float | None = None

class WalkForwardEvaluationReport(BaseModel):
    population: PopulationType
    population_name: str
    total_samples: int = 0
    min_train_size: int = 20
    step_size: int = 5
    num_folds: int = 0
    status: str = "INSUFFICIENT_DATA"
    status_reason: str = ""
    folds: list[WalkForwardFoldMetric] = Field(default_factory=list)
    model_aggregates: list[WalkForwardModelAggregate] = Field(default_factory=list)
    scientific_conclusions: list[str] = Field(default_factory=list)

class PopulationSeparationReport(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_runs: int = 0
    total_transitions: int = 0
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    populations: list[PopulationAuditSummary] = Field(default_factory=list)
    walk_forward_reports: dict[str, WalkForwardEvaluationReport] = Field(default_factory=dict)
    primary_insights: list[str] = Field(default_factory=list)
