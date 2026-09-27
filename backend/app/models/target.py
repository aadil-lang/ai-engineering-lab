from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import TargetType, ApplicationType

class ApplicationTarget(BaseModel):
    target_id: str = Field(default_factory=lambda: f"tgt_{uuid.uuid4().hex[:8]}")
    application_id: str | None = None
    application_type: str | None = None
    name: str
    target_type: TargetType = TargetType.WEB_APPLICATION
    base_url: str
    environment: str = "staging"
    version: str = "1.0.0"
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ApplicationTargetCreate(BaseModel):
    application_id: str | None = None
    application_type: str | None = None
    name: str
    target_type: TargetType = TargetType.WEB_APPLICATION
    base_url: str
    environment: str = "staging"
    version: str = "1.0.0"
    description: str = ""
    metadata: dict = Field(default_factory=dict)

