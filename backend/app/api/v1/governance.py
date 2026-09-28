from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query
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
    AuthorizationStatus,
    CanApplyResult,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.errors import (
    GovernanceError,
    RecommendationNotFoundError,
    ApprovalRequestNotFoundError,
    HumanIdentityRequiredError,
    AIAgentCannotApproveError,
    ChangeAuthorizationNotFoundError,
    AuthorizationExpiredError,
    EvidencePackageNotFoundError,
    PolicyViolationError,
)

router = APIRouter(prefix="/governance", tags=["Human Governance"])

# Singleton services for API
_repo = GovernanceRepository()
_evidence_svc = GovernanceEvidenceService(_repo)
_policy_svc = GovernancePolicyService(_repo)
_auth_svc = ChangeAuthorizationService(_repo, _evidence_svc)
_approval_svc = GovernanceApprovalService(_repo, _policy_svc, _evidence_svc, _auth_svc)


def get_authenticated_human(
    x_human_user: Optional[str] = Header(None, alias="X-Human-User"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates authenticated human identity.
    Rejects missing or AI agent credentials.
    """
    user = x_human_user or (authorization.replace("Bearer ", "").strip() if authorization else None)
    if not user or not user.strip():
        raise HTTPException(
            status_code=401,
            detail="Human authentication required. Header 'X-Human-User' or 'Authorization' must be provided.",
        )
    lowered = user.lower().strip()
    if (
        lowered.startswith("agent-")
        or lowered.startswith("ai-")
        or lowered.startswith("llm-")
        or "bot" in lowered
        or "autonomous" in lowered
    ):
        raise HTTPException(
            status_code=403,
            detail=f"Actor '{user}' is recognized as an AI agent. AI agents cannot authorize changes.",
        )
    return user.strip()


# Request bodies
class CreateApprovalRequestDTO(BaseModel):
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


class ApproveChangeDTO(BaseModel):
    decision_reason: str
    evidence_acknowledged: bool = True
    version_acknowledged: bool = True
    commit_acknowledged: bool = False
    authorization_scope: str = "PROMOTE"


class RejectChangeDTO(BaseModel):
    decision_reason: str


class RevokeAuthorizationDTO(BaseModel):
    reason: str


# --- Endpoints ---

# 1. Recommendations
@router.get("/recommendations", response_model=List[GovernanceRecommendation])
def list_recommendations():
    return _approval_svc.list_recommendations()


@router.get("/recommendations/{recommendation_id}", response_model=GovernanceRecommendation)
def get_recommendation(recommendation_id: str):
    try:
        return _approval_svc.get_recommendation(recommendation_id)
    except RecommendationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 2. Approval Requests
@router.post("/approval-requests", response_model=ApprovalRequest)
def create_approval_request(dto: CreateApprovalRequestDTO):
    try:
        return _approval_svc.create_approval_request(
            change_type=dto.change_type,
            subject_type=dto.subject_type,
            subject_id=dto.subject_id,
            evidence_package_id=dto.evidence_package_id,
            recommendation_id=dto.recommendation_id,
            current_version=dto.current_version,
            proposed_version=dto.proposed_version,
            proposed_commit_sha=dto.proposed_commit_sha,
            evaluation_snapshot_id=dto.evaluation_snapshot_id,
            lab_verification_id=dto.lab_verification_id,
            ci_verification_id=dto.ci_verification_id,
            risk_level=dto.risk_level,
        )
    except (EvidencePackageNotFoundError, PolicyViolationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approval-requests", response_model=List[ApprovalRequest])
def list_approval_requests(status: Optional[ApprovalRequestStatus] = None):
    return _approval_svc.list_approval_requests(status=status)


@router.get("/approval-requests/{approval_request_id}")
def get_approval_request(approval_request_id: str):
    try:
        req = _approval_svc.get_approval_request(approval_request_id)
        dec = _repo.get_decision_for_request(approval_request_id)
        auth = None
        if dec:
            auths = _repo.list_authorizations()
            matching = [a for a in auths if a.approval_request_id == approval_request_id]
            if matching:
                auth = matching[0]
        pkg = _repo.get_evidence_package(req.evidence_package_id)
        return {
            "approval_request": req,
            "decision": dec,
            "authorization": auth,
            "evidence_package": pkg,
        }
    except ApprovalRequestNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/approval-requests/{approval_request_id}/approve")
def approve_request(
    approval_request_id: str,
    dto: ApproveChangeDTO,
    human_user: str = Depends(get_authenticated_human),
):
    try:
        apr, dec, auth = _approval_svc.record_decision(
            approval_request_id=approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id=human_user,
            decision_reason=dto.decision_reason,
            actor_type=ActorType.HUMAN,
            evidence_acknowledged=dto.evidence_acknowledged,
            version_acknowledged=dto.version_acknowledged,
            commit_acknowledged=dto.commit_acknowledged,
            authorization_scope=dto.authorization_scope,
        )
        return {
            "approval_request": apr,
            "decision": dec,
            "authorization": auth,
        }
    except (ApprovalRequestNotFoundError, HumanIdentityRequiredError, AIAgentCannotApproveError, PolicyViolationError, AuthorizationExpiredError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approval-requests/{approval_request_id}/reject")
def reject_request(
    approval_request_id: str,
    dto: RejectChangeDTO,
    human_user: str = Depends(get_authenticated_human),
):
    try:
        apr, dec, auth = _approval_svc.record_decision(
            approval_request_id=approval_request_id,
            decision=DecisionType.REJECT,
            decision_maker_id=human_user,
            decision_reason=dto.decision_reason,
            actor_type=ActorType.HUMAN,
        )
        return {
            "approval_request": apr,
            "decision": dec,
        }
    except (ApprovalRequestNotFoundError, HumanIdentityRequiredError, AIAgentCannotApproveError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# 3. Authorizations
@router.get("/authorizations", response_model=List[ChangeAuthorization])
def list_authorizations(status: Optional[AuthorizationStatus] = None):
    return _repo.list_authorizations(status=status)


@router.get("/authorizations/{authorization_id}", response_model=ChangeAuthorization)
def get_authorization(authorization_id: str):
    try:
        return _auth_svc.get_authorization(authorization_id)
    except ChangeAuthorizationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


class CanApplyRequestDTO(BaseModel):
    change_type: RecommendationType
    subject_id: str
    target_version: Optional[str] = None
    target_commit_sha: Optional[str] = None
    current_evidence_package_id: Optional[str] = None
    requested_scope: str = "PROMOTE"


@router.post("/authorizations/{authorization_id}/can-apply", response_model=CanApplyResult)
def evaluate_can_apply(
    authorization_id: str,
    dto: CanApplyRequestDTO,
):
    """
    Evaluates whether a consequential change can be applied under the specified authorization.
    Deterministic gate returning GateDecision (AUTHORIZED or BLOCKED).
    """
    return _auth_svc.can_apply(
        change_type=dto.change_type,
        subject_id=dto.subject_id,
        authorization_id=authorization_id,
        target_version=dto.target_version,
        target_commit_sha=dto.target_commit_sha,
        current_evidence_package_id=dto.current_evidence_package_id,
        requested_scope=dto.requested_scope,
    )


@router.post("/authorizations/{authorization_id}/consume", response_model=ChangeAuthorization)
def consume_authorization(
    authorization_id: str,
    human_user: str = Depends(get_authenticated_human),
):
    try:
        return _auth_svc.consume_authorization(
            authorization_id=authorization_id,
            actor_id=human_user,
            actor_type=ActorType.HUMAN,
        )
    except ChangeAuthorizationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/authorizations/{authorization_id}/revoke", response_model=ChangeAuthorization)
def revoke_authorization(
    authorization_id: str,
    dto: RevokeAuthorizationDTO,
    human_user: str = Depends(get_authenticated_human),
):
    try:
        return _auth_svc.revoke_authorization(
            authorization_id=authorization_id,
            actor_id=human_user,
            reason=dto.reason,
            actor_type=ActorType.HUMAN,
        )
    except ChangeAuthorizationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 4. Evidence
@router.get("/evidence/{package_id}")
def get_evidence(package_id: str):
    try:
        pkg = _evidence_svc.get_evidence_package(package_id)
        is_valid = _evidence_svc.verify_package_integrity(pkg)
        return {"evidence_package": pkg, "is_valid": is_valid}
    except EvidencePackageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 5. Audit
@router.get("/audit", response_model=List[GovernanceAuditRecord])
def get_audit(
    subject_id: Optional[str] = None,
    approval_request_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    records = _repo.list_audit_records(subject_id=subject_id, approval_request_id=approval_request_id)
    return records[:limit]
