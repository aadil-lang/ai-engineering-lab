from __future__ import annotations
import uuid
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from backend.app.governance.models import (
    ChangeAuthorization,
    AuthorizationStatus,
    GateDecision,
    CanApplyResult,
    ActorType,
    GovernanceAuditRecord,
    RecommendationType,
    HumanDecision,
    DecisionType,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.errors import (
    ChangeAuthorizationNotFoundError,
    AuthorizationExpiredError,
    AuthorizationRevokedError,
    ConsequentialChangeBlockedError,
)


class ChangeAuthorizationService:
    """
    Manages the lifecycle and verification of ChangeAuthorizations.
    Enforces the central consequential change gate: can_apply().
    Guarantees that an authorization is scoped, time-bounded, version-specific,
    commit-specific, and cryptographically tied to verified evidence.
    """

    def __init__(
        self,
        repo: Optional[GovernanceRepository] = None,
        evidence_service: Optional[GovernanceEvidenceService] = None,
    ):
        self.repo = repo or GovernanceRepository()
        self.evidence_service = evidence_service or GovernanceEvidenceService(self.repo)

    def issue_authorization(
        self,
        approval_request_id: str,
        decision_id: str,
        authorized_change_type: RecommendationType,
        authorized_subject: str,
        evidence_package_id: str,
        evidence_package_hash: str,
        authorized_version: Optional[str] = None,
        authorized_commit_sha: Optional[str] = None,
        authorization_scope: str = "PROMOTE",
        validity_hours: int = 24,
    ) -> ChangeAuthorization:
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=validity_hours)).isoformat()
        auth_id = f"AUTH-{uuid.uuid4().hex[:12]}"

        auth = ChangeAuthorization(
            authorization_id=auth_id,
            approval_request_id=approval_request_id,
            decision_id=decision_id,
            authorized_change_type=authorized_change_type,
            authorized_subject=authorized_subject,
            authorized_version=authorized_version,
            authorized_commit_sha=authorized_commit_sha,
            authorization_scope=authorization_scope,
            evidence_package_id=evidence_package_id,
            evidence_package_hash=evidence_package_hash,
            issued_at=now.isoformat(),
            expires_at=expires_at,
            status=AuthorizationStatus.ACTIVE,
        )

        saved = self.repo.save_authorization(auth)

        # Audit log
        self._record_audit(
            event_type="AUTHORIZATION_ISSUED",
            actor_type=ActorType.SYSTEM,
            actor_id="governance-service",
            subject_type=authorized_change_type.value,
            subject_id=authorized_subject,
            new_state="ACTIVE",
            evidence_package_id=evidence_package_id,
            approval_request_id=approval_request_id,
            authorization_id=auth_id,
            details={
                "version": authorized_version,
                "commit_sha": authorized_commit_sha,
                "scope": authorization_scope,
            },
        )
        return saved

    def get_authorization(self, authorization_id: str) -> ChangeAuthorization:
        auth = self.repo.get_authorization(authorization_id)
        if not auth:
            raise ChangeAuthorizationNotFoundError(f"ChangeAuthorization '{authorization_id}' not found.")
        return auth

    def revoke_authorization(
        self,
        authorization_id: str,
        actor_id: str,
        reason: str,
        actor_type: ActorType = ActorType.HUMAN,
    ) -> ChangeAuthorization:
        auth = self.get_authorization(authorization_id)
        old_status = auth.status.value
        auth.status = AuthorizationStatus.REVOKED
        saved = self.repo.save_authorization(auth)

        self._record_audit(
            event_type="AUTHORIZATION_REVOKED",
            actor_type=actor_type,
            actor_id=actor_id,
            subject_type=auth.authorized_change_type.value,
            subject_id=auth.authorized_subject,
            previous_state=old_status,
            new_state="REVOKED",
            evidence_package_id=auth.evidence_package_id,
            approval_request_id=auth.approval_request_id,
            authorization_id=auth.authorization_id,
            details={"revocation_reason": reason},
        )
        return saved

    def consume_authorization(
        self,
        authorization_id: str,
        actor_id: str,
        actor_type: ActorType = ActorType.HUMAN,
    ) -> ChangeAuthorization:
        auth = self.get_authorization(authorization_id)
        old_status = auth.status.value
        auth.status = AuthorizationStatus.USED
        saved = self.repo.save_authorization(auth)

        self._record_audit(
            event_type="AUTHORIZATION_USED",
            actor_type=actor_type,
            actor_id=actor_id,
            subject_type=auth.authorized_change_type.value,
            subject_id=auth.authorized_subject,
            previous_state=old_status,
            new_state="USED",
            evidence_package_id=auth.evidence_package_id,
            approval_request_id=auth.approval_request_id,
            authorization_id=auth.authorization_id,
            details={"action": "applied_change"},
        )
        return saved

    def can_apply(
        self,
        change_type: RecommendationType,
        subject_id: str,
        authorization_id: Optional[str],
        target_version: Optional[str] = None,
        target_commit_sha: Optional[str] = None,
        current_evidence_package_id: Optional[str] = None,
        requested_scope: str = "PROMOTE",
    ) -> CanApplyResult:
        """
        Deterministic gate evaluating whether a consequential change is authorized.
        Returns CanApplyResult with AUTHORIZED or BLOCKED and structured explanations.
        """
        blockers: List[str] = []
        reasons: List[str] = []

        if not authorization_id:
            blockers.append("No authorization ID provided. Consequential changes require an explicit ChangeAuthorization.")
            return CanApplyResult(
                decision=GateDecision.BLOCKED,
                is_authorized=False,
                reasons=["No authorization provided."],
                blockers=blockers,
            )

        auth = self.repo.get_authorization(authorization_id)
        if not auth:
            blockers.append(f"ChangeAuthorization '{authorization_id}' does not exist.")
            return CanApplyResult(
                decision=GateDecision.BLOCKED,
                is_authorized=False,
                reasons=[f"Authorization '{authorization_id}' not found."],
                blockers=blockers,
            )

        # 1. Status Check
        if auth.status == AuthorizationStatus.REVOKED:
            blockers.append(f"ChangeAuthorization '{authorization_id}' has been REVOKED.")
        elif auth.status == AuthorizationStatus.USED:
            blockers.append(f"ChangeAuthorization '{authorization_id}' has already been USED.")
        elif auth.status == AuthorizationStatus.EXPIRED:
            blockers.append(f"ChangeAuthorization '{authorization_id}' has EXPIRED.")

        # 2. Expiration Time Check
        now_iso = datetime.now(timezone.utc).isoformat()
        if auth.expires_at < now_iso:
            blockers.append(f"ChangeAuthorization expired at {auth.expires_at} (current time {now_iso}).")

        # 3. Subject and Change Type Check
        if auth.authorized_change_type != change_type:
            blockers.append(
                f"Change type mismatch: authorization is for '{auth.authorized_change_type.value}', "
                f"but requested change is '{change_type.value}'."
            )
        if auth.authorized_subject != subject_id:
            blockers.append(
                f"Subject mismatch: authorization is for '{auth.authorized_subject}', "
                f"but requested subject is '{subject_id}'."
            )

        # 4. Scope Check
        if auth.authorization_scope != requested_scope and auth.authorization_scope != "ALL":
            blockers.append(
                f"Scope mismatch: authorization is for scope '{auth.authorization_scope}', "
                f"requested scope is '{requested_scope}'."
            )

        # 5. Version Specificity (e.g., v18 cannot authorize v19)
        if target_version is not None and auth.authorized_version is not None:
            if str(target_version) != str(auth.authorized_version):
                blockers.append(
                    f"Version mismatch: authorization is bound to version '{auth.authorized_version}', "
                    f"attempted to apply to version '{target_version}'."
                )

        # 6. Commit SHA Specificity (e.g., commit abc123 cannot authorize commit def456)
        if target_commit_sha is not None and auth.authorized_commit_sha is not None:
            if target_commit_sha != auth.authorized_commit_sha:
                blockers.append(
                    f"Commit SHA mismatch: authorization is bound to commit '{auth.authorized_commit_sha}', "
                    f"attempted to apply to commit '{target_commit_sha}'."
                )

        # 7. Evidence Integrity Check
        pkg_id = current_evidence_package_id or auth.evidence_package_id
        if pkg_id != auth.evidence_package_id:
            blockers.append(
                f"Evidence package mismatch: authorization is bound to evidence '{auth.evidence_package_id}', "
                f"current evidence is '{pkg_id}'."
            )
        else:
            try:
                pkg = self.evidence_service.get_evidence_package(pkg_id)
                if pkg.content_hash != auth.evidence_package_hash:
                    blockers.append(
                        f"Evidence package '{pkg_id}' content hash has changed since authorization was issued. "
                        f"Expected {auth.evidence_package_hash}, current {pkg.content_hash}."
                    )
            except Exception as e:
                blockers.append(f"Failed to verify evidence package '{pkg_id}': {str(e)}")

        # 8. Human Decision Verification
        decision = self.repo.get_decision(auth.decision_id)
        if not decision:
            blockers.append(f"Referenced HumanDecision '{auth.decision_id}' does not exist.")
        else:
            if decision.decision != DecisionType.APPROVE:
                blockers.append(f"HumanDecision was '{decision.decision.value}', not APPROVE.")
            if decision.actor_type != ActorType.HUMAN:
                blockers.append(f"Decision was made by non-human actor type: '{decision.actor_type.value}'.")
            if not decision.decision_maker_id or decision.decision_maker_id.startswith("agent-") or decision.decision_maker_id.startswith("ai-"):
                blockers.append(f"Decision maker ID '{decision.decision_maker_id}' appears to be an AI agent, not a human.")

        # Result formulation
        if blockers:
            self._record_audit(
                event_type="CHANGE_BLOCKED",
                actor_type=ActorType.SYSTEM,
                actor_id="governance-service",
                subject_type=change_type.value,
                subject_id=subject_id,
                authorization_id=authorization_id,
                details={"blockers": blockers, "target_version": target_version, "commit_sha": target_commit_sha},
            )
            return CanApplyResult(
                decision=GateDecision.BLOCKED,
                is_authorized=False,
                reasons=[f"Change blocked by {len(blockers)} governance invariant(s)."],
                authorization_id=authorization_id,
                blockers=blockers,
            )

        reasons.append("All governance invariants satisfied: valid human approval, exact artifact match, verified evidence hash.")
        return CanApplyResult(
            decision=GateDecision.AUTHORIZED,
            is_authorized=True,
            reasons=reasons,
            authorization_id=authorization_id,
            blockers=[],
        )

    def _record_audit(
        self,
        event_type: str,
        actor_type: ActorType,
        actor_id: str,
        subject_type: str,
        subject_id: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        evidence_package_id: Optional[str] = None,
        approval_request_id: Optional[str] = None,
        authorization_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        now_iso = datetime.now(timezone.utc).isoformat()
        event_id = f"EVT-{uuid.uuid4().hex[:12]}"
        raw = {
            "event_id": event_id,
            "event_type": event_type,
            "actor_type": actor_type.value,
            "actor_id": actor_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "timestamp": now_iso,
            "details": details or {},
        }
        content_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()
        rec = GovernanceAuditRecord(
            event_id=event_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            subject_type=subject_type,
            subject_id=subject_id,
            previous_state=previous_state,
            new_state=new_state,
            timestamp=now_iso,
            evidence_package_id=evidence_package_id,
            approval_request_id=approval_request_id,
            authorization_id=authorization_id,
            content_hash=content_hash,
            details=details or {},
        )
        self.repo.append_audit_record(rec)
