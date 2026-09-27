from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any
import uuid

from backend.app.models.enums import (
    CampaignStatus,
    CampaignType,
    RunnerType,
    ExecutionSource,
)


class CampaignConfiguration(BaseModel):
    target_id: str
    campaign_type: CampaignType = CampaignType.REAL_RELIABILITY
    test_case_ids: list[str] = Field(default_factory=list)
    runner_types: list[RunnerType] = Field(default_factory=lambda: [RunnerType.PLAYWRIGHT])
    execution_sources: list[ExecutionSource] = Field(default_factory=list)
    iterations_per_test_case: int = 1
    target_url_override: str | None = None
    natural_language_goal: str | None = None
    max_agent_steps: int = 10
    delay_between_runs_ms: int = 500
    stop_on_first_failure: bool = False
    stop_on_consecutive_failures: int | None = None
    environment_id: str = "local-development"
    description: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class CampaignSummaryReport(BaseModel):
    campaign_id: str
    target_id: str
    status: CampaignStatus
    campaign_type: CampaignType = CampaignType.REAL_RELIABILITY
    total_requested: int
    total_completed: int
    passed_count: int
    failed_count: int
    cancelled_count: int
    pass_rate: float
    total_duration_ms: int
    average_duration_ms: float
    sources_breakdown: dict[str, int] = Field(default_factory=dict)
    runners_breakdown: dict[str, int] = Field(default_factory=dict)
    transitions_generated: int = 0
    population_impact: dict[str, Any] = Field(default_factory=dict)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Campaign(BaseModel):
    campaign_id: str = Field(default_factory=lambda: f"camp_{uuid.uuid4().hex[:8]}")
    name: str
    description: str | None = None
    target_id: str
    campaign_type: CampaignType = CampaignType.REAL_RELIABILITY
    environment_id: str = "local-development"
    status: CampaignStatus = CampaignStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    finished_at: str | None = None
    requested_runs: int = 0
    completed_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    cancelled_runs: int = 0
    execution_sources: list[ExecutionSource] = Field(default_factory=list)
    configuration: CampaignConfiguration
    run_ids: list[str] = Field(default_factory=list)
    summary_report: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "system"
    configuration_version: str = "v1.0"


class CampaignCreate(BaseModel):
    name: str
    target_id: str
    campaign_type: CampaignType | None = None
    test_case_ids: list[str] = Field(default_factory=list)
    runner_types: list[RunnerType] = Field(default_factory=lambda: [RunnerType.PLAYWRIGHT])
    execution_sources: list[ExecutionSource] = Field(default_factory=list)
    iterations_per_test_case: int = 1
    target_url_override: str | None = None
    natural_language_goal: str | None = None
    max_agent_steps: int = 10
    delay_between_runs_ms: int = 500
    stop_on_first_failure: bool = False
    stop_on_consecutive_failures: int | None = None
    environment_id: str = "local-development"
    description: str | None = None
    created_by: str = "system"
    parameters: dict[str, Any] = Field(default_factory=dict)

