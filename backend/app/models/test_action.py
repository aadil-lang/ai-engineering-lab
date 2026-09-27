from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import ActionType, ActionStatus

class TestAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    action_type: ActionType
    description: str
    thought: str | None = None
    selector: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ActionStatus = ActionStatus.PENDING
    input_data: dict = Field(default_factory=dict)
    output_data: dict = Field(default_factory=dict)
    duration_ms: int = 0
    error_message: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
