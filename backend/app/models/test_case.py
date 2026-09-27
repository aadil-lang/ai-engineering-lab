from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import TestMode

class TestCase(BaseModel):
    test_case_id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    target_id: str
    name: str
    test_mode: TestMode = TestMode.FUNCTIONAL_QA
    description: str = ""
    steps: list[dict] = Field(default_factory=list)
    assertions: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TestCaseCreate(BaseModel):
    target_id: str
    name: str
    test_mode: TestMode = TestMode.FUNCTIONAL_QA
    description: str = ""
    steps: list[dict] = Field(default_factory=list)
    assertions: list[dict] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
