"""
Slice 8L — Unified Engineering Provenance & End-to-End Change Trace Models

Provides structured, append-only lifecycle event models that connect:
Request -> Implementation -> Git -> PR -> AI Review -> CI -> Application Context ->
Change Impact -> Regression Plan -> Lab Execution -> Evidence -> AI Evaluation ->
Diagnosis -> Remediation -> Governance Decision -> Authorization -> Change Retest ->
Post-Change Verification.

Core Principles:
1. Traceability Layer, not replacement: Subsystems remain authoritative for their own domain.
2. Canonical Engineering Lifecycle Event: References artifacts rather than duplicating domain models.
3. Cryptographic Chain: Tamper-evident linking via SHA-256(canonical_payload + previous_hash).
4. Append-Only: No mutations or deletions; corrections represented via EVENT_CORRECTION.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class ActorType(str, Enum):
    """Categorical classification of the entity causing or recording the event."""
    HUMAN = "HUMAN"
    AI_AGENT = "AI_AGENT"
    SYSTEM = "SYSTEM"
    CI = "CI"
    UNKNOWN = "UNKNOWN"


class LifecycleEventType(str, Enum):
    """Explicit deterministic lifecycle event classifications across the software lifecycle."""
    REQUEST_CREATED = "REQUEST_CREATED"

    IMPLEMENTATION_STARTED = "IMPLEMENTATION_STARTED"
    IMPLEMENTATION_COMPLETED = "IMPLEMENTATION_COMPLETED"

    LOCAL_TEST_STARTED = "LOCAL_TEST_STARTED"
    LOCAL_TEST_COMPLETED = "LOCAL_TEST_COMPLETED"

    GIT_COMMIT_CREATED = "GIT_COMMIT_CREATED"

    PULL_REQUEST_CREATED = "PULL_REQUEST_CREATED"
    PULL_REQUEST_UPDATED = "PULL_REQUEST_UPDATED"

    AI_REVIEW_STARTED = "AI_REVIEW_STARTED"
    AI_REVIEW_COMPLETED = "AI_REVIEW_COMPLETED"

    CI_STARTED = "CI_STARTED"
    CI_COMPLETED = "CI_COMPLETED"

    APPLICATION_CONTEXT_BOUND = "APPLICATION_CONTEXT_BOUND"
    APPLICATION_CONTEXT_VERIFIED = "APPLICATION_CONTEXT_VERIFIED"

    CHANGE_ANALYSIS_STARTED = "CHANGE_ANALYSIS_STARTED"
    CHANGE_ANALYSIS_COMPLETED = "CHANGE_ANALYSIS_COMPLETED"

    REGRESSION_PLAN_CREATED = "REGRESSION_PLAN_CREATED"
    REGRESSION_STARTED = "REGRESSION_STARTED"
    REGRESSION_COMPLETED = "REGRESSION_COMPLETED"

    LAB_RUN_STARTED = "LAB_RUN_STARTED"
    LAB_RUN_COMPLETED = "LAB_RUN_COMPLETED"

    EVIDENCE_CAPTURED = "EVIDENCE_CAPTURED"

    AI_EVALUATION_STARTED = "AI_EVALUATION_STARTED"
    AI_EVALUATION_COMPLETED = "AI_EVALUATION_COMPLETED"

    DIAGNOSIS_CREATED = "DIAGNOSIS_CREATED"
    DIAGNOSIS_VALIDATED = "DIAGNOSIS_VALIDATED"

    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    REMEDIATION_APPLIED = "REMEDIATION_APPLIED"

    GOVERNANCE_RECOMMENDATION_CREATED = "GOVERNANCE_RECOMMENDATION_CREATED"
    HUMAN_DECISION_RECORDED = "HUMAN_DECISION_RECORDED"

    CHANGE_AUTHORIZED = "CHANGE_AUTHORIZED"

    INDEPENDENT_RETEST_STARTED = "INDEPENDENT_RETEST_STARTED"
    INDEPENDENT_RETEST_COMPLETED = "INDEPENDENT_RETEST_COMPLETED"

    RELEASE_READINESS_EVALUATED = "RELEASE_READINESS_EVALUATED"
    POST_CHANGE_VERIFICATION_COMPLETED = "POST_CHANGE_VERIFICATION_COMPLETED"

    EVENT_CORRECTION = "EVENT_CORRECTION"


class EngineeringLifecycleEvent(BaseModel):
    """
    Canonical unit of engineering provenance.
    Immutable record forming an append-only cryptographic event chain.
    """
    event_id: str = Field(default_factory=lambda: f"evt_prov_{uuid.uuid4().hex[:12]}")
    sequence_number: int = 0
    event_type: LifecycleEventType
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Actor identity
    actor_type: ActorType = ActorType.SYSTEM
    actor_id: str = "system"

    # Context & Correlation
    correlation_id: str = Field(..., description="Unique thread identifier linking the end-to-end journey")
    parent_event_id: Optional[str] = None
    application_id: Optional[str] = None
    target_id: Optional[str] = None

    # Domain entity references (Reference, never duplicate)
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

    # Lifecycle entity references
    git_commit: Optional[str] = None
    pull_request_id: Optional[str] = None
    ci_run_id: Optional[str] = None
    context_id: Optional[str] = None

    # Structured metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Cryptographic integrity
    previous_event_hash: str = ""
    event_hash: str = ""


class ProvenanceChainVerificationResult(BaseModel):
    """Integrity audit result for the cryptographic event chain."""
    is_valid: bool
    total_events: int
    verified_events: int
    broken_event_id: Optional[str] = None
    violation_type: Optional[str] = None  # MODIFIED_EVENT | INCORRECT_PREVIOUS_HASH | BROKEN_SEQUENCE | DUPLICATE_EVENT | NONE
    details: str = "Chain integrity fully verified."


class ProvenanceTrace(BaseModel):
    """Aggregated end-to-end lifecycle trace for a correlation thread."""
    correlation_id: str
    events: List[EngineeringLifecycleEvent] = Field(default_factory=list)
    stages_present: List[str] = Field(default_factory=list)
    is_complete_lifecycle: bool = False
    total_events: int = 0
    summary: str = ""
