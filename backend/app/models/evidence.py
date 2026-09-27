from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import EvidenceType

class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: f"evi_{uuid.uuid4().hex[:8]}")
    run_id: str
    action_id: str | None = None
    evidence_type: EvidenceType
    title: str
    artifact_path: str | None = None
    mime_type: str = "application/json"
    payload: dict | str | list = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
