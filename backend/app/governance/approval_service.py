from __future__ import annotations
import uuid
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from backend.app.governance.models import (
    GovernanceRecommendation,
    ApprovalRequest,
    ApprovalRequestStatus,
    HumanDecision,
    ChangeAuthorization,
    RecommendationType,
    RiskLevel,
    DecisionType,
    ActorType,
    EvidencePackage,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.governance.errors import (
    RecommendationNotFoundError,
    ApprovalRequestNotFoundError,
    HumanIdentityRequiredError,
    AIAgentCannotApproveError,
    AuthorizationExpiredError,
    InvalidApprovalStateTransitionError,
    PolicyViolationError,
)


class GovernanceApprovalService:
    """
    Manages recommendations, approval requests, and human decisions.
    Strictly enforces that AI cannot approve changes and human identity is required.
    """

    def __init__(
        self,
        repo: Optional[GovernanceRepository] = None,
        policy_service: Optional[GovernancePolicyService] = None,
        evidence_service: Optional[GovernanceEvidenceService] = None,
        authorization_service: Optional[ChangeAuthorizationService] = None,
    ):
        self.repo = repo or GovernanceRepository()
        self.policy_service = policy_service or GovernancePolicyService(self.repo)
        self.evidence_service = evidence_service or GovernanceEvidenceService(self.repo)
        self.authorization_service = authorization_service or ChangeAuthorizationService(
            self.repo, self.evidence_service
        )

    # --- Recommendations ---

    def create_recommendation(
        self,
        recommendation_type: RecommendationType,
        subject_type: str,
        subject_id: str,
        source_system: str,
        proposed_action: str,
        rationale: str,
        source_run_id: Optional[str] = None,
        source_evaluation_id: Optional[str] = None,
        source_diagnosis_id: Optional[str] = None,
        source_evidence_ids: Optional[List[str]] = None,
        epistemic_status: str = "HYPOTHESIS",
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        validity_days: int = 7,
    ) -> GovernanceRecommendation:
        rec_id = f"REC-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=validity_days)).isoformat()

        effective_risk = self.policy_service.determine_effective_risk(
            change_type=recommendation_type,
            ai_proposed_risk=risk_level,
        )

        rec = GovernanceRecommendation(
            recommendation_id=rec_id,
            recommendation_type=recommendation_type,
            subject_type=subject_type,
            subject_id=subject_id,
            source_system=source_system,
            source_run_id=source_run_id,
            source_evaluation_id=source_evaluation_id,
            source_diagnosis_id=source_diagnosis_id,
            source_evidence_ids=source_evidence_ids or [],
            proposed_action=proposed_action,
            rationale=rationale,
            epistemic_status=epistemic_status,
            risk_level=risk_level,
            effective_risk=effective_risk,
            created_at=now.isoformat(),
            expires_at=expires_at,
        )
        saved = self.repo.save_recommendation(rec)

        self.authorization_service._record_audit(
            event_type="RECOMMENDATION_CREATED",
            actor_type=ActorType.AI_AGENT,
            actor_id=source_system,
            subject_type=subject_type,
            subject_id=subject_id,
            new_state="PROPOSED",
            details={
                "recommendation_id": rec_id,
                "proposed_action": proposed_action,
                "risk_level": risk_level.value,
                "effective_risk": effective_risk.value,
            },
        )
        return saved

    def get_recommendation(self, rec_id: str) -> GovernanceRecommendation:
        rec = self.repo.get_recommendation(rec_id)
        if not rec:
            raise RecommendationNotFoundError(f"Recommendation '{rec_id}' not found.")
        return rec

    def list_recommendations(self) -> List[GovernanceRecommendation]:
        return self.repo.list_recommendations()

    # --- Approval Requests ---

    def create_approval_request(
        self,
        change_type: RecommendationType,
        subject_type: str,
        subject_id: str,
        evidence_package_id: str,
        recommendation_id: Optional[str] = None,
        current_version: Optional[str] = None,
        proposed_version: Optional[str] = None,
        proposed_commit_sha: Optional[str] = None,
        evaluation_snapshot_id: Optional[str] = None,
        lab_verification_id: Optional[str] = None,
        ci_verification_id: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None,
        validity_days: int = 7,
    ) -> ApprovalRequest:
        # Verify evidence package
        evidence_pkg = self.evidence_service.get_evidence_package(evidence_package_id)

        # Determine effective risk
        proposed_risk = risk_level or RiskLevel.HIGH
        effective_risk = self.policy_service.determine_effective_risk(
            change_type=change_type,
            ai_proposed_risk=proposed_risk,
        )

        req_id = f"APR-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=validity_days)).isoformat()

        req = ApprovalRequest(
            approval_request_id=req_id,
            recommendation_id=recommendation_id,
            change_type=change_type,
            subject_type=subject_type,
            subject_id=subject_id,
            current_version=current_version,
            proposed_version=proposed_version,
            proposed_commit_sha=proposed_commit_sha,
            evaluation_snapshot_id=evaluation_snapshot_id or evidence_pkg.evaluation_snapshot_id,
            lab_verification_id=lab_verification_id or evidence_pkg.lab_verification_id,
            ci_verification_id=ci_verification_id or evidence_pkg.ci_run_id,
            evidence_package_id=evidence_package_id,
            risk_level=effective_risk,
            required_approval_count=1,
            status=ApprovalRequestStatus.PENDING,
            created_at=now.isoformat(),
            expires_at=expires_at,
        )

        # Policy validation
        compliant, violations = self.policy_service.evaluate_policy_compliance(req, evidence_pkg)
        if not compliant:
            raise PolicyViolationError(f"Approval request violates policy: {'; '.join(violations)}")

        saved = self.repo.save_approval_request(req)

        self.authorization_service._record_audit(
            event_type="APPROVAL_REQUESTED",
            actor_type=ActorType.SYSTEM,
            actor_id="governance-service",
            subject_type=subject_type,
            subject_id=subject_id,
            new_state="PENDING",
            evidence_package_id=evidence_package_id,
            approval_request_id=req_id,
            details={
                "change_type": change_type.value,
                "proposed_version": proposed_version,
                "proposed_commit_sha": proposed_commit_sha,
                "effective_risk": effective_risk.value,
            },
        )
        return saved

    def get_approval_request(self, req_id: str) -> ApprovalRequest:
        req = self.repo.get_approval_request(req_id)
        if not req:
            raise ApprovalRequestNotFoundError(f"ApprovalRequest '{req_id}' not found.")
        return req

    def list_approval_requests(self, status: Optional[ApprovalRequestStatus] = None) -> List[ApprovalRequest]:
        return self.repo.list_approval_requests(status=status)

    # --- Decision Processing ---

    def record_decision(
        self,
        approval_request_id: str,
        decision: DecisionType,
        decision_maker_id: str,
        decision_reason: str,
        actor_type: ActorType = ActorType.HUMAN,
        evidence_acknowledged: bool = False,
        version_acknowledged: bool = False,
        commit_acknowledged: bool = False,
        authorization_scope: str = "PROMOTE",
    ) -> Tuple[ApprovalRequest, HumanDecision, Optional[ChangeAuthorization]]:
        """
        Records human decision on an ApprovalRequest.
        Strictly enforces:
        1. Actor must be HUMAN. AI agents cannot approve changes.
        2. Explicit identity required.
        3. Acknowledgment checkboxes must be True for APPROVE.
        4. Issues ChangeAuthorization on APPROVE.
        """
        req = self.get_approval_request(approval_request_id)

        # Security check: AI Agent cannot approve
        if actor_type != ActorType.HUMAN:
            raise AIAgentCannotApproveError(
                f"Actor type '{actor_type.value}' is not permitted to make governance decisions. Only HUMAN actors may authorize changes."
            )

        # Identity validation
        if not decision_maker_id or not decision_maker_id.strip():
            raise HumanIdentityRequiredError("Explicit human decision maker ID is required.")

        lowered_id = decision_maker_id.lower().strip()
        if (
            lowered_id.startswith("agent-")
            or lowered_id.startswith("ai-")
            or lowered_id.startswith("llm-")
            or "bot" in lowered_id
            or "autonomous" in lowered_id
        ):
            raise AIAgentCannotApproveError(
                f"Decision maker ID '{decision_maker_id}' indicates an AI agent. Impersonation of human authority is forbidden."
            )

        # Status check
        if req.status != ApprovalRequestStatus.PENDING:
            raise InvalidApprovalStateTransitionError(
                f"ApprovalRequest '{approval_request_id}' is in status '{req.status.value}', expected PENDING."
            )

        # Expiration check
        now_iso = datetime.now(timezone.utc).isoformat()
        if req.expires_at and req.expires_at < now_iso:
            req.status = ApprovalRequestStatus.EXPIRED
            self.repo.save_approval_request(req)
            raise AuthorizationExpiredError(f"ApprovalRequest '{approval_request_id}' has expired.")

        # Acknowledgments for APPROVE
        if decision == DecisionType.APPROVE:
            if not evidence_acknowledged or not version_acknowledged:
                raise PolicyViolationError(
                    "Human approval requires explicit acknowledgment of verified evidence and artifact version."
                )
            if req.proposed_commit_sha and not commit_acknowledged:
                raise PolicyViolationError(
                    "Human approval for code changes requires explicit acknowledgment of the Git commit SHA."
                )

        now = datetime.now(timezone.utc).isoformat()
        decision_id = f"DEC-{uuid.uuid4().hex[:12]}"

        human_dec = HumanDecision(
            decision_id=decision_id,
            approval_request_id=approval_request_id,
            decision=decision,
            decision_maker_id=decision_maker_id,
            actor_type=ActorType.HUMAN,
            decision_timestamp=now,
            decision_reason=decision_reason,
            evidence_acknowledged=evidence_acknowledged,
            version_acknowledged=version_acknowledged,
            commit_acknowledged=commit_acknowledged,
        )
        saved_decision = self.repo.save_decision(human_dec)

        auth: Optional[ChangeAuthorization] = None

        if decision == DecisionType.APPROVE:
            req.status = ApprovalRequestStatus.APPROVED
            self.repo.save_approval_request(req)

            # Fetch evidence package to bind hash
            evidence_pkg = self.evidence_service.get_evidence_package(req.evidence_package_id)

            auth = self.authorization_service.issue_authorization(
                approval_request_id=req.approval_request_id,
                decision_id=decision_id,
                authorized_change_type=req.change_type,
                authorized_subject=req.subject_id,
                evidence_package_id=req.evidence_package_id,
                evidence_package_hash=evidence_pkg.content_hash,
                authorized_version=req.proposed_version,
                authorized_commit_sha=req.proposed_commit_sha,
                authorization_scope=authorization_scope,
            )

            self.authorization_service._record_audit(
                event_type="APPROVAL_APPROVED",
                actor_type=ActorType.HUMAN,
                actor_id=decision_maker_id,
                subject_type=req.subject_type,
                subject_id=req.subject_id,
                previous_state="PENDING",
                new_state="APPROVED",
                evidence_package_id=req.evidence_package_id,
                approval_request_id=req.approval_request_id,
                authorization_id=auth.authorization_id,
                details={"reason": decision_reason},
            )
        else:
            req.status = ApprovalRequestStatus.REJECTED
            self.repo.save_approval_request(req)

            self.authorization_service._record_audit(
                event_type="APPROVAL_REJECTED",
                actor_type=ActorType.HUMAN,
                actor_id=decision_maker_id,
                subject_type=req.subject_type,
                subject_id=req.subject_id,
                previous_state="PENDING",
                new_state="REJECTED",
                evidence_package_id=req.evidence_package_id,
                approval_request_id=req.approval_request_id,
                details={"reason": decision_reason},
            )

        return req, saved_decision, auth
