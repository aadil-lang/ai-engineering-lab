"""
Slice 8L — Unified Engineering Provenance API Router

Provides REST endpoints for:
- Appending lifecycle events to the immutable cryptographic chain
- Querying events by correlation_id, application_id, run_id, git_commit
- Generating end-to-end provenance traces
- Verifying cryptographic SHA-256 chain integrity
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.app.provenance.models import (
    EngineeringLifecycleEvent,
    ProvenanceTrace,
    ProvenanceChainVerificationResult,
    LifecycleEventType,
    ActorType,
)
from backend.app.provenance.service import ProvenanceService

router = APIRouter()

# Shared singleton service instance
_provenance_service = ProvenanceService()


def get_provenance_service() -> ProvenanceService:
    return _provenance_service


class CreateLifecycleEventRequest(BaseModel):
    correlation_id: str
    event_type: LifecycleEventType
    actor_type: ActorType = ActorType.SYSTEM
    actor_id: str = "system"
    application_id: Optional[str] = None
    target_id: Optional[str] = None
    run_id: Optional[str] = None
    test_case_id: Optional[str] = None
    change_set_id: Optional[str] = None
    plan_id: Optional[str] = None
    memory_id: Optional[str] = None
    evidence_id: Optional[str] = None
    diagnosis_id: Optional[str] = None
    remediation_id: Optional[str] = None
    governance_id: Optional[str] = None
    authorization_id: Optional[str] = None
    git_commit: Optional[str] = None
    pull_request_id: Optional[str] = None
    ci_run_id: Optional[str] = None
    context_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerifyChainRequest(BaseModel):
    correlation_id: Optional[str] = None


@router.post("/events", response_model=EngineeringLifecycleEvent)
def record_event(
    req: CreateLifecycleEventRequest,
    service: ProvenanceService = Depends(get_provenance_service)
):
    """Appends an event to the append-only cryptographic chain."""
    return service.record_event(
        event_type=req.event_type,
        correlation_id=req.correlation_id,
        actor_type=req.actor_type,
        actor_id=req.actor_id,
        application_id=req.application_id,
        target_id=req.target_id,
        run_id=req.run_id,
        test_case_id=req.test_case_id,
        change_set_id=req.change_set_id,
        plan_id=req.plan_id,
        memory_id=req.memory_id,
        evidence_id=req.evidence_id,
        diagnosis_id=req.diagnosis_id,
        remediation_id=req.remediation_id,
        governance_id=req.governance_id,
        authorization_id=req.authorization_id,
        git_commit=req.git_commit,
        pull_request_id=req.pull_request_id,
        ci_run_id=req.ci_run_id,
        context_id=req.context_id,
        parent_event_id=req.parent_event_id,
        metadata=req.metadata,
    )


@router.get("/events/{event_id}", response_model=EngineeringLifecycleEvent)
def get_event(
    event_id: str,
    service: ProvenanceService = Depends(get_provenance_service)
):
    """Retrieves an event by its unique ID."""
    evt = service.get_event(event_id)
    if not evt:
        raise HTTPException(status_code=404, detail=f"Lifecycle event '{event_id}' not found.")
    return evt


@router.get("/events", response_model=List[EngineeringLifecycleEvent])
def list_events(
    correlation_id: Optional[str] = None,
    application_id: Optional[str] = None,
    run_id: Optional[str] = None,
    git_commit: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    service: ProvenanceService = Depends(get_provenance_service)
):
    """Queries events with optional metadata filters."""
    return service.repo.list_events(
        correlation_id=correlation_id,
        application_id=application_id,
        run_id=run_id,
        git_commit=git_commit,
        limit=limit
    )


@router.get("/trace", response_model=ProvenanceTrace)
def get_trace(
    correlation_id: str = Query(..., description="Thread correlation ID"),
    service: ProvenanceService = Depends(get_provenance_service)
):
    """Retrieves the aggregated end-to-end trace for a correlation thread."""
    return service.get_provenance_trace(correlation_id)


@router.post("/verify", response_model=ProvenanceChainVerificationResult)
def verify_chain(
    req: VerifyChainRequest = Body(default_factory=VerifyChainRequest),
    service: ProvenanceService = Depends(get_provenance_service)
):
    """Audits the cryptographic SHA-256 event chain integrity."""
    return service.verify_chain(correlation_id=req.correlation_id)
