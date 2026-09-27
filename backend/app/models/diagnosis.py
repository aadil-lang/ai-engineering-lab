from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import FailureCategory, Severity, ClaimType, GroundingStatus

class DeterministicSignal(BaseModel):
    signal_type: str # e.g. "HTTP_ERROR", "CONSOLE_ERROR", "DOM_MISSING", "TIMEOUT", "ASSERTION_ERROR", "PAGE_ALERT"
    summary: str
    details: dict = Field(default_factory=dict)

class ReproductionStep(BaseModel):
    step_number: int
    action: str
    target: str | None = None
    expected: str | None = None
    observed: str | None = None

class EvidenceBundle(BaseModel):
    run_id: str
    target_id: str
    target_url: str
    test_mode: str
    natural_language_goal: str | None = None
    failed_action_index: int | None = None
    failed_action_type: str | None = None
    failed_action_selector: str | None = None
    error_message: str | None = None
    deterministic_signals: list[DeterministicSignal] = Field(default_factory=list)
    action_history: list[dict] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    failed_network_calls: list[dict] = Field(default_factory=list)
    page_alerts: list[str] = Field(default_factory=list)
    dom_error_snippet: str | None = None

class DiagnosisClaim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}")
    text: str
    claim_type: ClaimType
    evidence_refs: list[str] = Field(default_factory=list)
    grounding_status: GroundingStatus = GroundingStatus.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: str = ""

class GroundingSummary(BaseModel):
    total_claims: int = 0
    supported_claims: int = 0
    partially_supported_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    grounding_score: float = 1.0
    is_grounded: bool = True
    grounding_notes: list[str] = Field(default_factory=list)

class EngineeringDiagnosis(BaseModel):
    diagnosis_id: str = Field(default_factory=lambda: f"diag_{uuid.uuid4().hex[:8]}")
    run_id: str
    failure_id: str | None = None
    title: str
    root_cause_summary: str
    failure_category: FailureCategory
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)
    suspected_component: str # e.g. "Backend API (/checkout)", "Frontend Navigation Component", "Database Query", "AI Response Generator"
    deterministic_signals: list[DeterministicSignal] = Field(default_factory=list)
    reproduction_steps: list[ReproductionStep] = Field(default_factory=list)
    suggested_fix: str
    code_diff_suggestion: str | None = None
    regression_test_spec: str # Copyable Playwright / pytest regression test code
    severity: Severity = Severity.HIGH
    evidence_bundle_summary: str = ""
    
    # Grounding & Consistency Validation
    claims: list[DiagnosisClaim] = Field(default_factory=list)
    grounding_score: float = 1.0
    is_grounded: bool = True
    grounded_root_cause: str | None = None
    grounded_suspected_component: str | None = None
    grounded_confidence_score: float | None = None
    validation_notes: list[str] = Field(default_factory=list)
    
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
