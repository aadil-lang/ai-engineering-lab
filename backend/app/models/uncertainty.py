from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from backend.app.models.reliability import ConfusionMatrix, ClassificationMetrics


class UncertaintyBucketLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AbstentionDecision(str, Enum):
    ACCEPT = "ACCEPT"
    ABSTAIN = "ABSTAIN"


class ScientificVerdictStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DecisionPolicySelectionMethod(str, Enum):
    TRAIN_QUANTILE_25 = "TRAIN_QUANTILE_25"
    TRAIN_QUANTILE_50 = "TRAIN_QUANTILE_50"
    TRAIN_QUANTILE_75 = "TRAIN_QUANTILE_75"
    TRAIN_QUANTILE_90 = "TRAIN_QUANTILE_90"
    ACCEPT_ALL = "ACCEPT_ALL"


class PredictionUncertainty(BaseModel):
    """
    Individual prediction with mathematically derived posterior uncertainty bounds.
    """
    prediction_id: str
    prediction_run_id: str
    target_run_id: str
    application_id: str
    test_case_id: str
    timestamp: str
    budget_k: int
    calibration_k: int
    p_mean: float
    p_lower: float
    p_upper: float
    uncertainty_width: float
    effective_evidence: float
    observed_label: int
    decision: AbstentionDecision = AbstentionDecision.ACCEPT
    uncertainty_bucket: UncertaintyBucketLevel = UncertaintyBucketLevel.MEDIUM
    brier_contribution: float
    absolute_error: float


class UncertaintyBucketSummary(BaseModel):
    """
    Stratified performance summary for a specific uncertainty bucket.
    """
    bucket_level: UncertaintyBucketLevel
    lower_bound: float
    upper_bound: float
    sample_count: int
    failure_count: int
    mean_uncertainty: float
    mean_predicted_prob: float
    observed_failure_rate: float
    brier_score: float
    mean_absolute_error: float


class DecisionPolicy(BaseModel):
    """
    Abstention policy determined exclusively using training applications.
    """
    policy_id: str
    selection_method: DecisionPolicySelectionMethod
    threshold_tau: float
    training_applications: list[str]
    training_sample_count: int
    training_coverage: float
    training_selective_brier: float
    training_abstention_rate: float


class SelectivePredictionResult(BaseModel):
    """
    Evaluation of a frozen decision policy on an unseen test application.
    """
    policy_id: str
    threshold_tau: float
    test_application_id: str
    total_test_samples: int
    accepted_sample_count: int
    abstain_sample_count: int
    test_coverage: float
    test_abstention_rate: float
    accepted_failures_count: int
    accepted_passes_count: int
    accepted_failure_rate: float
    accepted_brier_score: float
    overall_brier_score: float
    selective_brier_improvement: float  # overall_brier - accepted_brier
    risk_reduction_pct: float


class RiskCoveragePoint(BaseModel):
    """
    A single point on the Risk-Coverage curve.
    """
    coverage: float
    abstention_rate: float
    threshold_tau: float
    accepted_count: int
    selective_brier: float
    selective_mae: float
    baseline_random_brier: float


class ApplicationShiftUncertainty(BaseModel):
    """
    Relationship between application-level distribution shift and predictive uncertainty.
    """
    application_id: str
    standardized_shift_mean: float
    raw_shift_mean: float
    relative_shift_mean: float
    mean_uncertainty_k0: float
    mean_uncertainty_k5: float
    uncertainty_reduction_k0_to_k5: float


class HypothesisVerdict(BaseModel):
    """
    Deterministic scientific verdict for a research hypothesis.
    """
    hypothesis_id: str
    title: str
    verdict: ScientificVerdictStatus
    empirical_metric_name: str
    empirical_metric_value: float | None = None
    threshold_criterion: str
    description: str
    is_deterministic: bool = True


class UncertaintyColdStartResult(BaseModel):
    """
    Cold-start metrics stratified by local budget K with uncertainty awareness.
    """
    application_id: str
    budget_k: int
    prediction_count: int
    observed_failures: int
    mean_predicted_prob: float
    mean_uncertainty: float
    median_uncertainty: float
    min_uncertainty: float
    max_uncertainty: float
    brier_score: float
    coverage_default_policy: float
    selective_brier_default_policy: float
    abstention_rate_default_policy: float


class UncertaintyExperiment(BaseModel):
    """
    Slice 7.1 Uncertainty-Aware Cold-Start Reliability Experiment Artifact.
    """
    experiment_id: str
    created_at: str
    protocol_version: str = "UncertaintyDecisionProtocol v1.0"
    parent_snapshot_id: str = "eval_snap_slice_7_0"
    snapshot_id: str = "eval_snap_slice_7_1"
    model_version: str = "v1.1-scaled-logistic"
    uncertainty_method_version: str = "v1.0-fisher-empirical-bayes"
    decision_policy_version: str = "v1.0-quantile-abstention"
    training_applications: list[str]
    test_applications: list[str]
    budget_k_values: list[int]
    total_eval_predictions: int
    cold_start_results: list[UncertaintyColdStartResult]
    predictions: list[PredictionUncertainty]
    decision_policies: list[DecisionPolicy]
    selective_results: list[SelectivePredictionResult]
    risk_coverage_curve: list[RiskCoveragePoint]
    uncertainty_buckets: list[UncertaintyBucketSummary]
    shift_uncertainty_analysis: list[ApplicationShiftUncertainty]
    hypotheses_verdicts: list[HypothesisVerdict]
    scientific_summary: list[str]
