from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import AssessmentDimension, Severity

class AssessmentFinding(BaseModel):
    finding_id: str = Field(default_factory=lambda: f"fnd_{uuid.uuid4().hex[:8]}")
    assessment_id: str
    dimension: AssessmentDimension
    severity: Severity = Severity.MEDIUM
    title: str
    description: str
    evidence_refs: list[str] = Field(default_factory=list)
    remediation: str = ""

class DimensionScore(BaseModel):
    dimension: AssessmentDimension
    score: float # 0.0 - 100.0
    status: str # PASS, WARN, FAIL
    summary: str
    findings_count: int = 0

class Assessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: f"asm_{uuid.uuid4().hex[:8]}")
    application_id: str
    overall_score: float = 0.0
    status: str = "PENDING" # PENDING, IN_PROGRESS, COMPLETED, FAILED
    dimensions: list[DimensionScore] = Field(default_factory=list)
    findings_ids: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
