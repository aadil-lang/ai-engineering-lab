from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import RunnerType, ExecutionSource

class LiveSessionStatus(str, Enum):
    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class LiveDogfoodingSession(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_live_{uuid.uuid4().hex[:8]}")
    run_id: str
    target_id: str
    application_id: str
    test_case_id: Optional[str] = None

    runner_type: RunnerType = RunnerType.PLAYWRIGHT
    execution_source: ExecutionSource = ExecutionSource.REAL_PLAYWRIGHT

    status: LiveSessionStatus = LiveSessionStatus.CREATED

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    current_step: int = 0
    total_steps: int = 0
    current_action: Optional[str] = None

    latest_screenshot_id: Optional[str] = None
    latest_event_sequence: int = 0

    subscriber_count: int = 0
