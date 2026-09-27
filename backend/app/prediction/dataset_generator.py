from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

class TelemetryFeatureVector(BaseModel):
    run_id: str
    target_id: str
    test_mode: str
    action_count: int
    mean_action_duration_ms: float
    max_action_duration_ms: float
    p95_action_duration_ms: float
    error_log_count: int
    flaky_retry_count: int
    dom_complexity_score: float
    network_request_count: int
    network_error_rate: float
    historical_failure_frequency: float
    label_failed: int # 0 or 1 for supervised learning

class PredictionResult(BaseModel):
    target_id: str
    failure_risk_probability: float # 0.0 - 1.0
    regression_risk_level: str # LOW, MEDIUM, HIGH, CRITICAL
    recommended_test_prioritization: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)

class BasePredictiveModel(ABC):
    """
    Contract for Future Machine Learning & Predictive Failure / Regression Risk Engine.
    Telemetry -> Feature Engineering -> ML -> Risk Prediction.
    """
    @abstractmethod
    def extract_features(self, run_id: str) -> TelemetryFeatureVector:
        pass

    @abstractmethod
    def predict_risk(self, feature_vector: TelemetryFeatureVector) -> PredictionResult:
        pass
