from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.governance.models import (
    GovernanceRecommendation,
    ApprovalRequest,
    ApprovalRequestStatus,
    HumanDecision,
    ChangeAuthorization,
    EvidencePackage,
    GovernanceAuditRecord,
    RecommendationType,
    RiskLevel,
    DecisionType,
    ActorType,
)


# 1. list_recommendations
class ListRecommendationsRequest(BaseModel):
    limit: Optional[int] = Field(default=50, description="Max recommendations to list")


class ListRecommendationsResponse(BaseModel):
    recommendations: List[GovernanceRecommendation]


# 2. get_recommendation
class GetRecommendationRequest(BaseModel):
    recommendation_id: str = Field(description="Unique recommendation ID")


class GetRecommendationResponse(BaseModel):
    recommendation: GovernanceRecommendation


# 3. create_approval_request
class CreateApprovalRequestRequest(BaseModel):
    change_type: RecommendationType
    subject_type: str
    subject_id: str
    evidence_package_id: str
    recommendation_id: Optional[str] = None
    current_version: Optional[str] = None
    proposed_version: Optional[str] = None
    proposed_commit_sha: Optional[str] = None
    evaluation_snapshot_id: Optional[str] = None
    lab_verification_id: Optional[str] = None
    ci_verification_id: Optional[str] = None
    risk_level: Optional[RiskLevel] = None


class CreateApprovalRequestResponse(BaseModel):
    approval_request: ApprovalRequest


# 4. get_approval_request
class GetApprovalRequestRequest(BaseModel):
    approval_request_id: str = Field(description="Unique approval request ID")


class GetApprovalRequestResponse(BaseModel):
    approval_request: ApprovalRequest
    decision: Optional[HumanDecision] = None
    authorization: Optional[ChangeAuthorization] = None
    evidence_package: Optional[EvidencePackage] = None


# 5. approve_change
class ApproveChangeRequest(BaseModel):
    approval_request_id: str
    decision_maker_id: str = Field(description="Authenticated human identity")
    decision_reason: str = Field(description="Human justification for approval")
    evidence_acknowledged: bool = Field(default=True, description="Human confirms review of evidence")
    version_acknowledged: bool = Field(default=True, description="Human confirms specific target version")
    commit_acknowledged: bool = Field(default=False, description="Human confirms specific target commit")
    authorization_scope: str = Field(default="PROMOTE", description="Scope of authorization (PROMOTE, MERGE, DEPLOY)")


class ApproveChangeResponse(BaseModel):
    approval_request: ApprovalRequest
    decision: HumanDecision
    authorization: ChangeAuthorization


# 6. reject_change
class RejectChangeRequest(BaseModel):
    approval_request_id: str
    decision_maker_id: str = Field(description="Authenticated human identity")
    decision_reason: str = Field(description="Human justification for rejection")


class RejectChangeResponse(BaseModel):
    approval_request: ApprovalRequest
    decision: HumanDecision


# 7. get_change_authorization
class GetChangeAuthorizationRequest(BaseModel):
    authorization_id: str = Field(description="Unique authorization ID")


class GetChangeAuthorizationResponse(BaseModel):
    authorization: ChangeAuthorization


# 8. revoke_change_authorization
class RevokeChangeAuthorizationRequest(BaseModel):
    authorization_id: str
    actor_id: str = Field(description="Identity revoking the authorization")
    revocation_reason: str = Field(description="Reason for revocation")


class RevokeChangeAuthorizationResponse(BaseModel):
    authorization: ChangeAuthorization


# 9. get_governance_evidence
class GetGovernanceEvidenceRequest(BaseModel):
    package_id: str = Field(description="Unique evidence package ID")


class GetGovernanceEvidenceResponse(BaseModel):
    evidence_package: EvidencePackage
    is_valid: bool


# 10. get_governance_audit
class GetGovernanceAuditRequest(BaseModel):
    subject_id: Optional[str] = None
    approval_request_id: Optional[str] = None
    limit: Optional[int] = Field(default=50, description="Max audit entries")


class GetGovernanceAuditResponse(BaseModel):
    audit_records: List[GovernanceAuditRecord]
