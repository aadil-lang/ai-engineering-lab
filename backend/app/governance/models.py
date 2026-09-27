from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    CODE_CHANGE = "CODE_CHANGE"
    PROMPT_CHANGE = "PROMPT_CHANGE"
    MODEL_CONFIGURATION_CHANGE = "MODEL_CONFIGURATION_CHANGE"
    RAG_CONFIGURATION_CHANGE = "RAG_CONFIGURATION_CHANGE"
    TOOL_PERMISSION_CHANGE = "TOOL_PERMISSION_CHANGE"
    DEPLOYMENT = "DEPLOYMENT"
    ROLLBACK = "ROLLBACK"
    OTHER = "OTHER"


class ApprovalRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class AuthorizationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActorType(str, Enum):
    SYSTEM = "SYSTEM"
    AI_AGENT = "AI_AGENT"
    HUMAN = "HUMAN"


class GateDecision(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED = "BLOCKED"


class GovernanceState(str, Enum):
    PROPOSED = "PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    AUTHORIZED = "AUTHORIZED"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"
    BLOCKED = "BLOCKED"


class GovernanceRecommendation(BaseModel):
    recommendation_id: str
    recommendation_type: RecommendationType
    subject_type: str
    subject_id: str
    source_system: str
    source_run_id: Optional[str] = None
    source_evaluation_id: Optional[str] = None
    source_diagnosis_id: Optional[str] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    proposed_action: str
    rationale: str
    epistemic_status: str = "HYPOTHESIS"
    risk_level: RiskLevel = RiskLevel.MEDIUM  # AI proposed risk
    effective_risk: Optional[RiskLevel] = None  # Determined by policy
    created_at: str
    expires_at: Optional[str] = None


class EvidencePackage(BaseModel):
    package_id: str
    subject_type: str
    subject_id: str
    git_commit_sha: Optional[str] = None
    prompt_version: Optional[str] = None
    model_version: Optional[str] = None
    evaluation_snapshot_id: Optional[str] = None
    ci_run_id: Optional[str] = None
    lab_verification_id: Optional[str] = None
    diagnosis_ids: List[str] = Field(default_factory=list)
    recommendation_ids: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    verification_results: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    content_hash: str  # SHA-256


class ApprovalRequest(BaseModel):
    approval_request_id: str
    recommendation_id: Optional[str] = None
    change_type: RecommendationType
    subject_type: str
    subject_id: str
    current_version: Optional[str] = None
    proposed_version: Optional[str] = None
    proposed_commit_sha: Optional[str] = None
    evaluation_snapshot_id: Optional[str] = None
    lab_verification_id: Optional[str] = None
    ci_verification_id: Optional[str] = None
    evidence_package_id: str
    risk_level: RiskLevel
    required_approval_count: int = 1
    status: ApprovalRequestStatus = ApprovalRequestStatus.PENDING
    created_at: str
    expires_at: Optional[str] = None


class HumanDecision(BaseModel):
    decision_id: str
    approval_request_id: str
    decision: DecisionType
    decision_maker_id: str
    actor_type: ActorType = ActorType.HUMAN
    decision_timestamp: str
    decision_reason: str
    evidence_acknowledged: bool
    version_acknowledged: bool
    commit_acknowledged: bool


class ChangeAuthorization(BaseModel):
    authorization_id: str
    approval_request_id: str
    decision_id: str
    authorized_change_type: RecommendationType
    authorized_subject: str
    authorized_version: Optional[str] = None
    authorized_commit_sha: Optional[str] = None
    authorization_scope: str = "PROMOTE"
    evidence_package_id: str
    evidence_package_hash: str
    issued_at: str
    expires_at: str
    status: AuthorizationStatus = AuthorizationStatus.ACTIVE


class ApprovalPolicy(BaseModel):
    policy_id: str
    name: str
    change_type: RecommendationType
    risk_level: RiskLevel
    required_approvals: int = 1
    required_evidence: List[str] = Field(default_factory=list)
    required_verifications: List[str] = Field(default_factory=list)
    human_role_requirements: List[str] = Field(default_factory=list)
    enabled: bool = True
    version: int = 1


class GovernanceAuditRecord(BaseModel):
    event_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str
    subject_type: str
    subject_id: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    timestamp: str
    evidence_package_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    authorization_id: Optional[str] = None
    content_hash: str
    details: Dict[str, Any] = Field(default_factory=dict)


class CanApplyResult(BaseModel):
    decision: GateDecision
    is_authorized: bool
    reasons: List[str] = Field(default_factory=list)
    authorization_id: Optional[str] = None
    blockers: List[str] = Field(default_factory=list)
