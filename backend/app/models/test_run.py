from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import TestMode, RunStatus, RunnerType, ExecutionSource, CampaignType
from backend.app.models.test_action import TestAction

class TestRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    application_id: str
    application_version: str = "1.0.0"
    test_mode: TestMode = TestMode.FUNCTIONAL_QA
    runner_type: RunnerType = RunnerType.MOCK
    execution_source: ExecutionSource = ExecutionSource.UNKNOWN
    test_case_id: str | None = None
    status: RunStatus = RunStatus.QUEUED
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None
    duration_ms: int = 0
    environment_id: str = "env_default"
    browser_context_id: str | None = None
    session_id: str | None = None
    natural_language_goal: str | None = None
    max_agent_steps: int = 10
    agent_thought_trace: list[dict] = Field(default_factory=list)
    actions: list[TestAction] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    failure_ids: list[str] = Field(default_factory=list)
    metrics_summary: dict[str, float] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)
    feature_vector_version: str = "v1.0-temporal"
    campaign_id: str | None = None
    campaign_type: CampaignType | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TestRunCreate(BaseModel):
    application_id: str
    test_mode: TestMode = TestMode.FUNCTIONAL_QA
    runner_type: RunnerType = RunnerType.MOCK
    execution_source: ExecutionSource = ExecutionSource.UNKNOWN
    test_case_id: str | None = None
    application_version: str = "1.0.0"
    environment_id: str = "env_default"
    simulate_failure: bool = False
    custom_scenario: str | None = None
    target_url_override: str | None = None
    natural_language_goal: str | None = None
    max_agent_steps: int = 10
    action_delay_ms: int = 150 # Delay per step to simulate real network/browser work
    campaign_id: str | None = None
    campaign_type: CampaignType | None = None



