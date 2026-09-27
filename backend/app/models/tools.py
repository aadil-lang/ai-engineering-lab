from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class ToolMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    ACTION = "ACTION"


class HealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNRELIABLE = "UNRELIABLE"
    UNKNOWN = "UNKNOWN"


class SessionMode(str, Enum):
    exploratory = "exploratory"
    regression = "regression"
    reliability = "reliability"
    adversarial = "adversarial"
    production_readiness = "production-readiness"


class DiagnosisDepth(str, Enum):
    standard = "standard"
    deep = "deep"


class EvidenceCategory(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIZED = "HYPOTHESIZED"


class ToolErrorCode(str, Enum):
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    FAILURE_NOT_FOUND = "FAILURE_NOT_FOUND"
    PREDICTION_NOT_FOUND = "PREDICTION_NOT_FOUND"
    EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RELIABILITY_ABSTAINED = "RELIABILITY_ABSTAINED"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    INVALID_REQUEST = "INVALID_REQUEST"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ToolProvenance(BaseModel):
    snapshot_id: str = "eval_snap_slice_7_1"
    experiment_id: str | None = None
    model_version: str = "v1.1-scaled-logistic"
    feature_schema_version: str = "v1.0-temporal"
    dataset_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_run_ids: list[str] = Field(default_factory=list)


class ToolResponseMetadata(BaseModel):
    tool_name: str
    tool_version: str = "1.0"
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str | None = None
    application_id: str | None = None
    provenance: ToolProvenance = Field(default_factory=ToolProvenance)
    execution_time_ms: float = 0.0


class ToolError(BaseModel):
    error_code: ToolErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    recoverable: bool = False


T = TypeVar("T")


class ToolResponseEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ToolError | None = None
    metadata: ToolResponseMetadata


# -------------------------------------------------------------
# Tool 1: inspect_application (READ_ONLY)
# -------------------------------------------------------------
class InspectApplicationRequest(BaseModel):
    application_id: str
    environment: str = "staging"
    base_url: str | None = None
    session_id: str | None = None


class InspectApplicationResponse(BaseModel):
    application_id: str
    name: str
    environment: str
    base_url: str
    application_type: str
    known_routes: list[str]
    known_capabilities: list[str]
    last_tested_at: str | None
    latest_reliability_state: HealthState
    total_runs: int
    total_failures: int
    available_evidence_types: list[str]


# -------------------------------------------------------------
# Tool 2: start_test_session (ACTION)
# -------------------------------------------------------------
class StartTestSessionRequest(BaseModel):
    application_id: str
    mode: SessionMode = SessionMode.reliability
    scope: str = "full"
    max_duration_seconds: int = 300
    idempotency_key: str | None = None


class StartTestSessionResponse(BaseModel):
    session_id: str
    application_id: str
    mode: SessionMode
    status: str
    started_at: str
    constraints: dict[str, Any]
    is_idempotent_replay: bool = False


# -------------------------------------------------------------
# Tool 3: get_application_health (READ_ONLY)
# -------------------------------------------------------------
class GetApplicationHealthRequest(BaseModel):
    application_id: str
    session_id: str | None = None


class GetApplicationHealthResponse(BaseModel):
    application_id: str
    health_state: HealthState
    failure_probability: float | None
    uncertainty: float | None
    uncertainty_interval: tuple[float, float] | None
    evidence_count: int
    coverage: float | None
    last_updated: str
    confidence_state: str
    abstention_state: bool
    reason: str


# -------------------------------------------------------------
# Tool 4: get_prediction (READ_ONLY)
# -------------------------------------------------------------
class GetPredictionRequest(BaseModel):
    application_id: str
    test_case_id: str | None = None
    session_id: str | None = None


class GetPredictionResponse(BaseModel):
    prediction_id: str
    application_id: str
    probability: float
    prediction_interval: tuple[float, float]
    model_version: str
    feature_schema_version: str
    calibration_k: int
    effective_evidence: float
    uncertainty_width: float
    created_at: str
    source_experiment: str
    source_snapshot: str
    source_run_ids: list[str]


# -------------------------------------------------------------
# Tool 5: get_uncertainty (READ_ONLY)
# -------------------------------------------------------------
class GetUncertaintyRequest(BaseModel):
    application_id: str
    session_id: str | None = None


class GetUncertaintyResponse(BaseModel):
    prediction_id: str
    application_id: str
    mean_probability: float
    lower_bound: float
    upper_bound: float
    uncertainty_width: float
    effective_evidence: float
    covariate_shift: float
    abstention_recommended: bool
    uncertainty_category: str
    reason: str


# -------------------------------------------------------------
# Tool 6: list_failures (READ_ONLY, Paginated)
# -------------------------------------------------------------
class ListFailuresRequest(BaseModel):
    application_id: str | None = None
    session_id: str | None = None
    severity: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class FailureSummaryItem(BaseModel):
    failure_id: str
    run_id: str
    timestamp: str
    severity: str
    category: str
    route: str | None = None
    action: str | None = None
    error_signature: str
    reproducibility: str
    evidence_reference: str | None = None


class ListFailuresResponse(BaseModel):
    failures: list[FailureSummaryItem]
    next_cursor: str | None = None
    total_available: int
    has_more: bool = False


# -------------------------------------------------------------
# Tool 7: get_failure (READ_ONLY)
# -------------------------------------------------------------
class GetFailureRequest(BaseModel):
    failure_id: str
    session_id: str | None = None


class GetFailureResponse(BaseModel):
    failure_id: str
    application_id: str
    run_id: str
    session_id: str | None = None
    timestamp: str
    route: str | None = None
    action_sequence: list[str] = Field(default_factory=list)
    error: str
    stack_trace: str | None = None
    screenshot_reference: str | None = None
    network_evidence: list[dict[str, Any]] = Field(default_factory=list)
    console_evidence: list[str] = Field(default_factory=list)
    reproduction_status: str
    related_predictions: list[dict[str, Any]] = Field(default_factory=list)


# -------------------------------------------------------------
# Tool 8: diagnose_failure (READ_ONLY)
# -------------------------------------------------------------
class DiagnoseFailureRequest(BaseModel):
    failure_id: str
    depth: DiagnosisDepth = DiagnosisDepth.standard
    session_id: str | None = None


class DiagnosticEvidenceFact(BaseModel):
    statement: str
    category: EvidenceCategory  # OBSERVED, INFERRED, HYPOTHESIZED
    source: str


class DiagnoseFailureResponse(BaseModel):
    failure_id: str
    failure_class: str
    probable_root_causes: list[DiagnosticEvidenceFact]
    supporting_evidence: list[DiagnosticEvidenceFact]
    contradicting_evidence: list[DiagnosticEvidenceFact]
    confidence: float
    recommended_next_actions: list[str]


# -------------------------------------------------------------
# Tool 9: get_evidence (READ_ONLY)
# -------------------------------------------------------------
class GetEvidenceRequest(BaseModel):
    evidence_id: str
    session_id: str | None = None


class GetEvidenceResponse(BaseModel):
    evidence_id: str
    type: str
    timestamp: str
    source: str
    content: Any
    redactions_applied: list[str] = Field(default_factory=list)
    sha256_hash: str


# -------------------------------------------------------------
# Tool 10: get_reliability_summary (READ_ONLY)
# -------------------------------------------------------------
class GetReliabilitySummaryRequest(BaseModel):
    application_id: str
    session_id: str | None = None


class GetReliabilitySummaryResponse(BaseModel):
    application_id: str
    overall_state: HealthState
    failure_probability: float
    uncertainty: float
    evidence_count: int
    recent_failures_count: int
    distribution_shift: float
    abstention_state: bool
    top_risks: list[str]
    recommended_next_actions: list[str]
