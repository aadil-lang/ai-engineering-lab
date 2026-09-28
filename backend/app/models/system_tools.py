"""
Slice 8M — System Diagnostics, Readiness & Demonstration MCP Tool Models

Defines request and response schemas for:
- get_environment_diagnostics
- get_system_readiness
- get_release_manifest
- run_canonical_demonstration
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.system.models import (
    DiagnosticCheck,
    EngineeringLabReadiness,
    EngineeringLabReleaseManifest,
    DemonstrationScenarioResult,
)


class GetEnvironmentDiagnosticsRequest(BaseModel):
    pass


class GetEnvironmentDiagnosticsResponse(BaseModel):
    checks: List[DiagnosticCheck] = Field(default_factory=list)


class GetSystemReadinessRequest(BaseModel):
    pass


class GetSystemReadinessResponse(BaseModel):
    readiness: EngineeringLabReadiness


class GetReleaseManifestRequest(BaseModel):
    pass


class GetReleaseManifestResponse(BaseModel):
    manifest: EngineeringLabReleaseManifest


class RunCanonicalDemonstrationRequest(BaseModel):
    correlation_id: Optional[str] = None
    governor_actor_id: str = "lead_qa_engineer_alice"
    target_id: str = "real_question_generator_local"


class RunCanonicalDemonstrationResponse(BaseModel):
    result: DemonstrationScenarioResult
