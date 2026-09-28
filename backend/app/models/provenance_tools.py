"""
Pydantic schemas for Slice 8L Unified Engineering Provenance MCP Tools.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.provenance.models import (
    EngineeringLifecycleEvent,
    ProvenanceTrace,
    ProvenanceChainVerificationResult,
    LifecycleEventType,
    ActorType,
)


class RecordLifecycleEventRequest(BaseModel):
    correlation_id: str = Field(..., description="Unique thread identifier linking the end-to-end journey")
    event_type: LifecycleEventType = Field(..., description="Type of engineering lifecycle event")
    actor_type: ActorType = Field(default=ActorType.SYSTEM, description="Actor type (HUMAN, AI_AGENT, SYSTEM, CI)")
    actor_id: str = Field(default="system", description="Identifier of the actor")
    application_id: Optional[str] = Field(None, description="Associated application ID")
    target_id: Optional[str] = Field(None, description="Associated target ID")
    run_id: Optional[str] = Field(None, description="Associated test run ID")
    test_case_id: Optional[str] = Field(None, description="Associated test case ID")
    change_set_id: Optional[str] = Field(None, description="Associated change set ID")
    plan_id: Optional[str] = Field(None, description="Associated regression plan ID")
    memory_id: Optional[str] = Field(None, description="Associated memory ID")
    evidence_id: Optional[str] = Field(None, description="Associated evidence ID")
    diagnosis_id: Optional[str] = Field(None, description="Associated diagnosis ID")
    remediation_id: Optional[str] = Field(None, description="Associated remediation ID")
    governance_id: Optional[str] = Field(None, description="Associated governance ID")
    authorization_id: Optional[str] = Field(None, description="Associated authorization ID")
    git_commit: Optional[str] = Field(None, description="Associated Git commit SHA")
    pull_request_id: Optional[str] = Field(None, description="Associated pull request ID")
    ci_run_id: Optional[str] = Field(None, description="Associated CI run ID")
    context_id: Optional[str] = Field(None, description="Associated application context ID")
    parent_event_id: Optional[str] = Field(None, description="Parent event ID for corrections or sub-workflows")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary structured metadata")


class RecordLifecycleEventResponse(BaseModel):
    event: EngineeringLifecycleEvent


class GetLifecycleEventRequest(BaseModel):
    event_id: str = Field(..., description="Lifecycle event ID to retrieve")


class GetLifecycleEventResponse(BaseModel):
    event: Optional[EngineeringLifecycleEvent] = None


class GetProvenanceTraceRequest(BaseModel):
    correlation_id: str = Field(..., description="Correlation ID to trace from inception to verification")


class GetProvenanceTraceResponse(BaseModel):
    trace: ProvenanceTrace


class VerifyProvenanceChainRequest(BaseModel):
    correlation_id: Optional[str] = Field(None, description="Optional correlation ID to restrict audit to, or full chain")


class VerifyProvenanceChainResponse(BaseModel):
    result: ProvenanceChainVerificationResult
