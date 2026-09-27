from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import FailureCategory, Severity

class Failure(BaseModel):
    failure_id: str = Field(default_factory=lambda: f"fail_{uuid.uuid4().hex[:8]}")
    run_id: str
    action_id: str | None = None
    category: FailureCategory
    severity: Severity = Severity.HIGH
    title: str
    message: str
    stack_trace: str | None = None
    suggested_remediation: str | None = None
    failed_action: str | None = None
    selector: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
