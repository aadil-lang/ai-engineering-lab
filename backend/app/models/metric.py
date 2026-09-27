from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class Metric(BaseModel):
    metric_id: str = Field(default_factory=lambda: f"met_{uuid.uuid4().hex[:8]}")
    run_id: str
    name: str
    value: float
    unit: str
    tags: dict[str, str] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
