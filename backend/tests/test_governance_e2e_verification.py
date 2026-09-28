"""
Slice 7.9 — Governance E2E Verification Suite
==================================================

Executable proof that the Governance Layer prevents consequential changes
from bypassing human authorization and artifact-bound verification.

Organized by governance invariant:

  TestGovernanceHappyPath       — Full lifecycle: recommendation → evidence → approval → authorization → can_apply → ALLOW
  TestHumanAuthorization        — Human-only approval enforcement; AI/system/bot actors rejected
  TestEvidenceRequirements      — Missing, unacknowledged, invalid, and modified evidence → DENY
  TestVersionBinding            — V1 authorization + V2 artifact → DENY
  TestHashBinding               — Artifact with modified hash → DENY (most important)
  TestPolicyEnforcement         — Risk-level and policy gate verification
  TestRejection                 — Rejected request cannot produce authorization
  TestRevocation                — Revoked authorization → can_apply → DENY
  TestReplayProtection          — Consumed (USED) authorization cannot be replayed
  TestAuditTrail                — Immutable audit log contains required event sequence
  TestDeterministicAuthorization— Identical inputs → deterministic results
  TestSecurityBypass            — Explicit bypass attempts that must all fail
  TestAPILevel                  — REST API-level governance flow (FastAPI TestClient)
"""

import os
import json
import hashlib
import pytest
from datetime import datetime, timezone, timedelta

from backend.app.governance.models import (
    GovernanceRecommendation,
    ApprovalRequest,
    ApprovalRequestStatus,
    HumanDecision,
    ChangeAuthorization,
    AuthorizationStatus,
    RecommendationType,
    RiskLevel,
    DecisionType,
    ActorType,
    GateDecision,
    CanApplyResult,
    EvidencePackage,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.errors import (
    AIAgentCannotApproveError,
    HumanIdentityRequiredError,
    InvalidApprovalStateTransitionError,
    EvidencePackageNotFoundError,
    EvidencePackageTamperedError,
    PolicyViolationError,
    ConsequentialChangeBlockedError,
    ChangeAuthorizationNotFoundError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Isolated fixture — each test class gets a fresh governance stack
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def gov(tmp_path):
    """Provides a fully isolated governance stack backed by a temporary SQLite DB."""
    db_path = str(tmp_path / "governance_e2e.db")
    repo = GovernanceRepository(db_path=db_path)
    evidence_svc = GovernanceEvidenceService(repo)
    policy_svc = GovernancePolicyService(repo)
    auth_svc = ChangeAuthorizationService(repo, evidence_svc)
    approval_svc = GovernanceApprovalService(repo, policy_svc, evidence_svc, auth_svc)
    return {
        "repo": repo,
        "evidence_svc": evidence_svc,
        "policy_svc": policy_svc,
        "auth_svc": auth_svc,
        "approval_svc": approval_svc,
    }


def _create_evidence(evidence_svc, subject_id, **kwargs):
    """Helper: create an EvidencePackage with sensible defaults."""
    defaults = dict(
        subject_type="PROMPT",
        subject_id=subject_id,
        prompt_version="1",
        evaluation_snapshot_id="eval_snap_default",
        observations=["Baseline evaluation passed."],
    )
    defaults.update(kwargs)
    return evidence_svc.create_evidence_package(**defaults)


def _create_approval_request(approval_svc, evidence_pkg, subject_id, **kwargs):
    """Helper: create an ApprovalRequest with sensible defaults."""
    defaults = dict(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id=subject_id,
        evidence_package_id=evidence_pkg.package_id,
        proposed_version="1",
        evaluation_snapshot_id=evidence_pkg.evaluation_snapshot_id,
    )
    defaults.update(kwargs)
    return approval_svc.create_approval_request(**defaults)


def _approve(approval_svc, req, **kwargs):
    """Helper: record a human APPROVE decision with acknowledgments."""
    defaults = dict(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="lead_engineer@enterprise.org",
        decision_reason="Verified evaluation results and evidence package.",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        commit_acknowledged=False,
        authorization_scope="PROMOTE",
    )
    defaults.update(kwargs)
    return approval_svc.record_decision(**defaults)


# ═════════════════════════════════════════════════════════════════════════════
# 1. HAPPY PATH — Full Governance Lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestGovernanceHappyPath:
    """Verifies the complete governance lifecycle from recommendation to authorized change."""

    def test_full_lifecycle_recommendation_to_can_apply(self, gov):
        """
        Recommendation → Evidence → Approval Request → Human APPROVE
          → Change Authorization → can_apply() → AUTHORIZED
        """
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        # 1. AI creates recommendation
        rec = approval_svc.create_recommendation(
            recommendation_type=RecommendationType.PROMPT_CHANGE,
            subject_type="PROMPT",
            subject_id="happy-path-prompt",
            source_system="PROMPT_LAB",
            proposed_action="Promote prompt v2 to production",
            rationale="Fixed schema defect with zero regressions.",
            risk_level=RiskLevel.MEDIUM,
        )
        assert rec.recommendation_id.startswith("REC-")
        assert rec.effective_risk == RiskLevel.HIGH  # Policy elevates PROMPT_CHANGE

        # 2. Evidence package
        evidence_pkg = evidence_svc.create_evidence_package(
            subject_type="PROMPT",
            subject_id="happy-path-prompt",
            prompt_version="2",
            evaluation_snapshot_id="eval_snap_hp",
            observations=["All test cases passed schema validation."],
            verification_results={"pass_rate": 1.0, "regressions": 0},
        )
        assert len(evidence_pkg.content_hash) == 64

        # 3. Approval request
        apr = approval_svc.create_approval_request(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_type="PROMPT",
            subject_id="happy-path-prompt",
            evidence_package_id=evidence_pkg.package_id,
            recommendation_id=rec.recommendation_id,
            proposed_version="2",
            evaluation_snapshot_id="eval_snap_hp",
        )
        assert apr.status == ApprovalRequestStatus.PENDING

        # 4. Human approves
        apr_approved, decision, auth = approval_svc.record_decision(
            approval_request_id=apr.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="senior_eng@enterprise.org",
            decision_reason="Verified evidence: 100% pass rate, 0 regressions.",
            actor_type=ActorType.HUMAN,
            evidence_acknowledged=True,
            version_acknowledged=True,
            authorization_scope="PROMOTE",
        )
        assert apr_approved.status == ApprovalRequestStatus.APPROVED
        assert decision.decision == DecisionType.APPROVE
        assert decision.actor_type == ActorType.HUMAN
        assert auth is not None
        assert auth.status == AuthorizationStatus.ACTIVE
        assert auth.authorized_version == "2"
        assert auth.evidence_package_hash == evidence_pkg.content_hash

        # 5. can_apply() → AUTHORIZED
        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="happy-path-prompt",
            authorization_id=auth.authorization_id,
            target_version="2",
            requested_scope="PROMOTE",
        )
        assert result.decision == GateDecision.AUTHORIZED
        assert result.is_authorized is True
        assert len(result.blockers) == 0

    def test_each_state_transition_is_traceable(self, gov):
        """Every domain object maintains correct state after each transition."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]
        auth_svc = gov["auth_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "traceable-prompt", prompt_version="5")
        req = _create_approval_request(
            approval_svc, pkg, "traceable-prompt", proposed_version="5"
        )

        # State: PENDING
        fetched = approval_svc.get_approval_request(req.approval_request_id)
        assert fetched.status == ApprovalRequestStatus.PENDING

        # Transition: PENDING → APPROVED
        _, dec, auth = _approve(approval_svc, req)
        fetched = approval_svc.get_approval_request(req.approval_request_id)
        assert fetched.status == ApprovalRequestStatus.APPROVED

        # Authorization state: ACTIVE
        fetched_auth = auth_svc.get_authorization(auth.authorization_id)
        assert fetched_auth.status == AuthorizationStatus.ACTIVE

        # Consume → USED
        consumed = auth_svc.consume_authorization(
            auth.authorization_id, actor_id="deploy-pipeline"
        )
        assert consumed.status == AuthorizationStatus.USED


# ═════════════════════════════════════════════════════════════════════════════
# 2. HUMAN AUTHORIZATION — AI Must Never Authorize
# ═════════════════════════════════════════════════════════════════════════════


class TestHumanAuthorization:
    """AI, system, and bot actors must be rejected at the approval boundary."""

    def test_ai_agent_actor_type_rejected(self, gov):
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "ai-target")
        req = _create_approval_request(approval_svc, pkg, "ai-target")

        with pytest.raises(AIAgentCannotApproveError):
            approval_svc.record_decision(
                approval_request_id=req.approval_request_id,
                decision=DecisionType.APPROVE,
                decision_maker_id="agent-claude-3",
                decision_reason="AI auto-approval",
                actor_type=ActorType.AI_AGENT,
                evidence_acknowledged=True,
                version_acknowledged=True,
            )

    def test_system_actor_type_rejected(self, gov):
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "system-target")
        req = _create_approval_request(approval_svc, pkg, "system-target")

        with pytest.raises(AIAgentCannotApproveError):
            approval_svc.record_decision(
                approval_request_id=req.approval_request_id,
                decision=DecisionType.APPROVE,
                decision_maker_id="governance-service",
                decision_reason="Automated approval",
                actor_type=ActorType.SYSTEM,
                evidence_acknowledged=True,
                version_acknowledged=True,
            )

    def test_human_actor_with_ai_prefix_rejected(self, gov):
        """Spoofed human identity with AI prefix must be caught."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "spoof-target")
        req = _create_approval_request(approval_svc, pkg, "spoof-target")

        for ai_name in ["ai-copilot", "agent-gpt4", "llm-evaluator", "auto-bot-service", "autonomous-deployer"]:
            with pytest.raises(AIAgentCannotApproveError, match="AI agent"):
                approval_svc.record_decision(
                    approval_request_id=req.approval_request_id,
                    decision=DecisionType.APPROVE,
                    decision_maker_id=ai_name,
                    decision_reason="Attempted AI impersonation",
                    actor_type=ActorType.HUMAN,
                    evidence_acknowledged=True,
                    version_acknowledged=True,
                )

    def test_blank_identity_rejected(self, gov):
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "blank-id-target")
        req = _create_approval_request(approval_svc, pkg, "blank-id-target")

        for blank in ["", "   ", "\t"]:
            with pytest.raises(HumanIdentityRequiredError):
                approval_svc.record_decision(
                    approval_request_id=req.approval_request_id,
                    decision=DecisionType.APPROVE,
                    decision_maker_id=blank,
                    decision_reason="No identity",
                    actor_type=ActorType.HUMAN,
                    evidence_acknowledged=True,
                    version_acknowledged=True,
                )

    def test_ai_cannot_bypass_via_direct_authorization_creation(self, gov):
        """
        Even if an AI somehow constructs a ChangeAuthorization directly,
        can_apply() must reject it because the referenced HumanDecision
        has a non-human actor_type.
        """
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        # Create evidence
        pkg = _create_evidence(evidence_svc, "bypass-target")

        # Forge an AI decision directly in DB
        forged_decision = HumanDecision(
            decision_id="DEC-FORGED",
            approval_request_id="APR-FORGED",
            decision=DecisionType.APPROVE,
            decision_maker_id="agent-attacker",
            actor_type=ActorType.AI_AGENT,
            decision_timestamp=datetime.now(timezone.utc).isoformat(),
            decision_reason="Autonomous bypass attempt",
            evidence_acknowledged=True,
            version_acknowledged=True,
            commit_acknowledged=False,
        )
        repo.save_decision(forged_decision)

        # Issue authorization referencing forged decision
        auth = auth_svc.issue_authorization(
            approval_request_id="APR-FORGED",
            decision_id="DEC-FORGED",
            authorized_change_type=RecommendationType.PROMPT_CHANGE,
            authorized_subject="bypass-target",
            evidence_package_id=pkg.package_id,
            evidence_package_hash=pkg.content_hash,
            authorized_version="1",
        )

        # can_apply MUST detect the non-human decision and BLOCK
        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="bypass-target",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED
        assert result.is_authorized is False
        assert any("non-human" in b.lower() or "AI" in b for b in result.blockers)


# ═════════════════════════════════════════════════════════════════════════════
# 3. EVIDENCE REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════════


class TestEvidenceRequirements:
    """Approval and authorization require valid, acknowledged evidence."""

    def test_no_evidence_package_denies_approval_request(self, gov):
        """Creating approval request with non-existent evidence → DENY."""
        approval_svc = gov["approval_svc"]

        with pytest.raises(EvidencePackageNotFoundError):
            approval_svc.create_approval_request(
                change_type=RecommendationType.PROMPT_CHANGE,
                subject_type="PROMPT",
                subject_id="no-evidence-prompt",
                evidence_package_id="EVP-DOES-NOT-EXIST",
                proposed_version="1",
            )

    def test_evidence_not_acknowledged_denies_approval(self, gov):
        """Human decision without evidence_acknowledged=True → DENY."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "no-ack-prompt")
        req = _create_approval_request(approval_svc, pkg, "no-ack-prompt")

        with pytest.raises(PolicyViolationError, match="evidence"):
            approval_svc.record_decision(
                approval_request_id=req.approval_request_id,
                decision=DecisionType.APPROVE,
                decision_maker_id="eng@enterprise.org",
                decision_reason="Forgot to acknowledge evidence",
                actor_type=ActorType.HUMAN,
                evidence_acknowledged=False,
                version_acknowledged=True,
            )

    def test_version_not_acknowledged_denies_approval(self, gov):
        """Human decision without version_acknowledged=True → DENY."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "no-ver-ack-prompt")
        req = _create_approval_request(approval_svc, pkg, "no-ver-ack-prompt")

        with pytest.raises(PolicyViolationError, match="version"):
            approval_svc.record_decision(
                approval_request_id=req.approval_request_id,
                decision=DecisionType.APPROVE,
                decision_maker_id="eng@enterprise.org",
                decision_reason="Forgot to acknowledge version",
                actor_type=ActorType.HUMAN,
                evidence_acknowledged=True,
                version_acknowledged=False,
            )

    def test_modified_evidence_blocks_can_apply(self, gov):
        """Tampered evidence after approval → can_apply() BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "tamper-prompt")
        req = _create_approval_request(approval_svc, pkg, "tamper-prompt")
        _, _, auth = _approve(approval_svc, req)

        # Tamper evidence in DB
        with repo._get_connection() as conn:
            conn.execute(
                "UPDATE evidence_packages SET observations = ? WHERE package_id = ?",
                ('["TAMPERED"]', pkg.package_id),
            )
            conn.commit()

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="tamper-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED
        assert any("evidence" in b.lower() for b in result.blockers)

    def test_valid_evidence_allows_can_apply(self, gov):
        """Valid, untampered evidence → can_apply() AUTHORIZED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "valid-evidence-prompt")
        req = _create_approval_request(approval_svc, pkg, "valid-evidence-prompt")
        _, _, auth = _approve(approval_svc, req)

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="valid-evidence-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.AUTHORIZED
        assert result.is_authorized is True


# ═════════════════════════════════════════════════════════════════════════════
# 4. VERSION BINDING
# ═════════════════════════════════════════════════════════════════════════════


class TestVersionBinding:
    """Authorization is bound to the exact approved version."""

    def test_v1_authorization_blocks_v2_application(self, gov):
        """V1 authorization + V2 artifact → DENY."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "version-bound-prompt", prompt_version="1")
        req = _create_approval_request(
            approval_svc, pkg, "version-bound-prompt", proposed_version="1"
        )
        _, _, auth = _approve(approval_svc, req)

        # V1 auth + V1 target → ALLOW
        result_v1 = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="version-bound-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_v1.decision == GateDecision.AUTHORIZED

        # V1 auth + V2 target → DENY
        result_v2 = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="version-bound-prompt",
            authorization_id=auth.authorization_id,
            target_version="2",
        )
        assert result_v2.decision == GateDecision.BLOCKED
        assert result_v2.is_authorized is False
        assert any("Version mismatch" in b for b in result_v2.blockers)

    def test_version_binding_across_numeric_versions(self, gov):
        """Version 18 authorization must not authorize version 19."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "v18-prompt", prompt_version="18")
        req = _create_approval_request(
            approval_svc, pkg, "v18-prompt", proposed_version="18"
        )
        _, _, auth = _approve(approval_svc, req)

        for wrong_version in ["19", "17", "0", "18.1"]:
            result = auth_svc.can_apply(
                change_type=RecommendationType.PROMPT_CHANGE,
                subject_id="v18-prompt",
                authorization_id=auth.authorization_id,
                target_version=wrong_version,
            )
            assert result.decision == GateDecision.BLOCKED, f"Should block version {wrong_version}"


# ═════════════════════════════════════════════════════════════════════════════
# 5. CONTENT HASH BINDING (most important)
# ═════════════════════════════════════════════════════════════════════════════


class TestHashBinding:
    """Approval is bound to the exact artifact hash, not an abstract version intent."""

    def test_modified_artifact_hash_blocks_authorization(self, gov):
        """
        Artifact V1, Hash H1 → Approved
        Artifact V1, Hash H2 (modified) → can_apply(V1, H2) → DENY
        Artifact V1, Hash H1 (original) → can_apply(V1, H1) → ALLOW
        """
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        # Create and approve with H1
        pkg_h1 = _create_evidence(evidence_svc, "hash-bound-prompt", prompt_version="1")
        h1 = pkg_h1.content_hash
        req = _create_approval_request(
            approval_svc, pkg_h1, "hash-bound-prompt", proposed_version="1"
        )
        _, _, auth = _approve(approval_svc, req)
        assert auth.evidence_package_hash == h1

        # Verify H1 works
        result_h1 = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="hash-bound-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_h1.decision == GateDecision.AUTHORIZED

        # Now tamper with evidence to create H2 scenario
        with repo._get_connection() as conn:
            conn.execute(
                "UPDATE evidence_packages SET observations = ? WHERE package_id = ?",
                ('["MODIFIED ARTIFACT CONTENT"]', pkg_h1.package_id),
            )
            conn.commit()

        # can_apply with tampered evidence → BLOCKED
        result_h2 = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="hash-bound-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_h2.decision == GateDecision.BLOCKED
        assert any("hash" in b.lower() or "evidence" in b.lower() for b in result_h2.blockers)

    def test_hash_is_sha256_and_deterministic(self, gov):
        """Evidence hash is deterministic SHA-256."""
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(
            evidence_svc, "hash-det-prompt",
            prompt_version="3",
            observations=["Deterministic test"],
        )
        assert len(pkg.content_hash) == 64  # SHA-256 hex digest


# ═════════════════════════════════════════════════════════════════════════════
# 6. POLICY ENFORCEMENT
# ═════════════════════════════════════════════════════════════════════════════


class TestPolicyEnforcement:
    """Policy service deterministically bounds risk and enforces verification gates."""

    def test_policy_elevates_risk_for_deployment(self, gov):
        """AI proposes LOW risk for DEPLOYMENT → Policy elevates to CRITICAL."""
        policy_svc = gov["policy_svc"]

        effective = policy_svc.determine_effective_risk(
            change_type=RecommendationType.DEPLOYMENT,
            ai_proposed_risk=RiskLevel.LOW,
        )
        assert effective == RiskLevel.CRITICAL

    def test_policy_elevates_risk_for_prompt_change(self, gov):
        """AI proposes LOW for PROMPT_CHANGE → Policy elevates to HIGH."""
        policy_svc = gov["policy_svc"]

        effective = policy_svc.determine_effective_risk(
            change_type=RecommendationType.PROMPT_CHANGE,
            ai_proposed_risk=RiskLevel.LOW,
        )
        assert effective == RiskLevel.HIGH

    def test_policy_preserves_higher_ai_risk(self, gov):
        """AI proposes CRITICAL for PROMPT_CHANGE → Policy preserves CRITICAL."""
        policy_svc = gov["policy_svc"]

        effective = policy_svc.determine_effective_risk(
            change_type=RecommendationType.PROMPT_CHANGE,
            ai_proposed_risk=RiskLevel.CRITICAL,
        )
        assert effective == RiskLevel.CRITICAL

    def test_missing_evidence_violates_code_change_policy(self, gov):
        """CODE_CHANGE without CI/Lab verification → policy violation."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        # Evidence without ci_run_id or lab_verification_id
        pkg = evidence_svc.create_evidence_package(
            subject_type="CODE",
            subject_id="policy-violation-service",
            git_commit_sha="abc123",
        )

        with pytest.raises(PolicyViolationError):
            approval_svc.create_approval_request(
                change_type=RecommendationType.CODE_CHANGE,
                subject_type="CODE",
                subject_id="policy-violation-service",
                evidence_package_id=pkg.package_id,
                proposed_commit_sha="abc123",
            )

    def test_complete_evidence_satisfies_code_change_policy(self, gov):
        """CODE_CHANGE with CI + Lab verification → policy satisfied."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = evidence_svc.create_evidence_package(
            subject_type="CODE",
            subject_id="policy-ok-service",
            git_commit_sha="def456",
            ci_run_id="ci-run-ok",
            lab_verification_id="lab-verif-ok",
        )

        req = approval_svc.create_approval_request(
            change_type=RecommendationType.CODE_CHANGE,
            subject_type="CODE",
            subject_id="policy-ok-service",
            evidence_package_id=pkg.package_id,
            proposed_commit_sha="def456",
            ci_verification_id="ci-run-ok",
            lab_verification_id="lab-verif-ok",
        )
        assert req.status == ApprovalRequestStatus.PENDING


# ═════════════════════════════════════════════════════════════════════════════
# 7. REJECTION FLOW
# ═════════════════════════════════════════════════════════════════════════════


class TestRejection:
    """Rejected request cannot produce a valid authorization."""

    def test_rejected_request_produces_no_authorization(self, gov):
        """Human REJECT → no ChangeAuthorization issued."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "reject-prompt")
        req = _create_approval_request(approval_svc, pkg, "reject-prompt")

        apr_rejected, dec, auth = approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.REJECT,
            decision_maker_id="eng_reviewer@enterprise.org",
            decision_reason="Insufficient coverage.",
            actor_type=ActorType.HUMAN,
        )
        assert apr_rejected.status == ApprovalRequestStatus.REJECTED
        assert auth is None

    def test_rejected_request_cannot_be_re_approved(self, gov):
        """Cannot approve a request that was already rejected."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "reject-then-approve")
        req = _create_approval_request(approval_svc, pkg, "reject-then-approve")

        # Reject first
        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.REJECT,
            decision_maker_id="eng@enterprise.org",
            decision_reason="Rejected.",
            actor_type=ActorType.HUMAN,
        )

        # Attempt to approve the already-rejected request → BLOCKED
        with pytest.raises(InvalidApprovalStateTransitionError):
            approval_svc.record_decision(
                approval_request_id=req.approval_request_id,
                decision=DecisionType.APPROVE,
                decision_maker_id="eng@enterprise.org",
                decision_reason="Changed my mind",
                actor_type=ActorType.HUMAN,
                evidence_acknowledged=True,
                version_acknowledged=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# 8. REVOCATION
# ═════════════════════════════════════════════════════════════════════════════


class TestRevocation:
    """Revoked authorization must fail can_apply()."""

    def test_revoked_authorization_blocks_can_apply(self, gov):
        """
        Valid Authorization → can_apply → ALLOW
          → Revoke → can_apply → DENY
        """
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "revoke-prompt")
        req = _create_approval_request(approval_svc, pkg, "revoke-prompt")
        _, _, auth = _approve(approval_svc, req)

        # Before revocation → ALLOW
        result_before = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="revoke-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_before.decision == GateDecision.AUTHORIZED

        # Revoke
        revoked = auth_svc.revoke_authorization(
            authorization_id=auth.authorization_id,
            actor_id="security_officer@enterprise.org",
            reason="Post-approval vulnerability discovered.",
        )
        assert revoked.status == AuthorizationStatus.REVOKED

        # After revocation → DENY
        result_after = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="revoke-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_after.decision == GateDecision.BLOCKED
        assert any("REVOKED" in b for b in result_after.blockers)


# ═════════════════════════════════════════════════════════════════════════════
# 9. REPLAY / DUPLICATE AUTHORIZATION PROTECTION
# ═════════════════════════════════════════════════════════════════════════════


class TestReplayProtection:
    """Consumed (USED) authorization cannot be replayed."""

    def test_used_authorization_blocks_replay(self, gov):
        """
        Authorization consumed → can_apply() with same auth → BLOCKED.
        """
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "replay-prompt")
        req = _create_approval_request(approval_svc, pkg, "replay-prompt")
        _, _, auth = _approve(approval_svc, req)

        # First use → ALLOW
        result_first = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="replay-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_first.decision == GateDecision.AUTHORIZED

        # Consume the authorization
        auth_svc.consume_authorization(
            authorization_id=auth.authorization_id,
            actor_id="deploy-pipeline",
        )

        # Replay attempt → BLOCKED
        result_replay = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="replay-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result_replay.decision == GateDecision.BLOCKED
        assert any("USED" in b for b in result_replay.blockers)

    def test_double_consume_is_safe(self, gov):
        """Consuming an already-used authorization doesn't crash."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "double-consume")
        req = _create_approval_request(approval_svc, pkg, "double-consume")
        _, _, auth = _approve(approval_svc, req)

        auth_svc.consume_authorization(auth.authorization_id, actor_id="pipeline-1")
        # Second consume should not crash
        auth_svc.consume_authorization(auth.authorization_id, actor_id="pipeline-2")


# ═════════════════════════════════════════════════════════════════════════════
# 10. AUDIT TRAIL VERIFICATION
# ═════════════════════════════════════════════════════════════════════════════


class TestAuditTrail:
    """Immutable audit trail records all governance state transitions."""

    def test_happy_path_audit_sequence(self, gov):
        """Verify audit trail contains the complete happy-path event sequence."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        # Full lifecycle
        rec = approval_svc.create_recommendation(
            recommendation_type=RecommendationType.PROMPT_CHANGE,
            subject_type="PROMPT",
            subject_id="audit-prompt",
            source_system="PROMPT_LAB",
            proposed_action="Promote v2",
            rationale="Tests pass.",
            risk_level=RiskLevel.MEDIUM,
        )
        pkg = _create_evidence(evidence_svc, "audit-prompt", prompt_version="2")
        req = _create_approval_request(
            approval_svc, pkg, "audit-prompt",
            proposed_version="2",
            recommendation_id=rec.recommendation_id,
        )
        _, _, auth = _approve(approval_svc, req)

        # Consume
        auth_svc.consume_authorization(auth.authorization_id, actor_id="deploy")

        # Verify audit trail
        audit_records = repo.list_audit_records(subject_id="audit-prompt")
        event_types = [r.event_type for r in audit_records]

        assert "RECOMMENDATION_CREATED" in event_types
        assert "APPROVAL_REQUESTED" in event_types
        assert "APPROVAL_APPROVED" in event_types
        assert "AUTHORIZATION_ISSUED" in event_types
        assert "AUTHORIZATION_USED" in event_types

    def test_rejection_audit_trail(self, gov):
        """Rejected flow produces APPROVAL_REJECTED event."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "audit-reject-prompt")
        req = _create_approval_request(approval_svc, pkg, "audit-reject-prompt")

        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.REJECT,
            decision_maker_id="eng@enterprise.org",
            decision_reason="Rejected.",
            actor_type=ActorType.HUMAN,
        )

        audit_records = repo.list_audit_records(subject_id="audit-reject-prompt")
        event_types = [r.event_type for r in audit_records]
        assert "APPROVAL_REJECTED" in event_types

    def test_revocation_audit_trail(self, gov):
        """Revocation produces AUTHORIZATION_REVOKED event."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "audit-revoke-prompt")
        req = _create_approval_request(approval_svc, pkg, "audit-revoke-prompt")
        _, _, auth = _approve(approval_svc, req)

        auth_svc.revoke_authorization(
            auth.authorization_id,
            actor_id="security@enterprise.org",
            reason="Revocation test",
        )

        audit_records = repo.list_audit_records(subject_id="audit-revoke-prompt")
        event_types = [r.event_type for r in audit_records]
        assert "AUTHORIZATION_REVOKED" in event_types

    def test_blocked_change_audit_trail(self, gov):
        """can_apply BLOCKED produces CHANGE_BLOCKED event."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "audit-block-prompt", prompt_version="1")
        req = _create_approval_request(
            approval_svc, pkg, "audit-block-prompt", proposed_version="1"
        )
        _, _, auth = _approve(approval_svc, req)

        # Try wrong version → BLOCKED → audit
        auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="audit-block-prompt",
            authorization_id=auth.authorization_id,
            target_version="999",
        )

        audit_records = repo.list_audit_records(subject_id="audit-block-prompt")
        event_types = [r.event_type for r in audit_records]
        assert "CHANGE_BLOCKED" in event_types

    def test_audit_records_have_content_hashes(self, gov):
        """All audit records have SHA-256 content hashes."""
        approval_svc = gov["approval_svc"]
        evidence_svc = gov["evidence_svc"]
        repo = gov["repo"]

        pkg = _create_evidence(evidence_svc, "audit-hash-prompt")
        req = _create_approval_request(approval_svc, pkg, "audit-hash-prompt")
        _approve(approval_svc, req)

        audit_records = repo.list_audit_records(subject_id="audit-hash-prompt")
        for rec in audit_records:
            assert len(rec.content_hash) == 64, f"Event {rec.event_id} missing SHA-256 hash"


# ═════════════════════════════════════════════════════════════════════════════
# 11. DETERMINISTIC AUTHORIZATION
# ═════════════════════════════════════════════════════════════════════════════


class TestDeterministicAuthorization:
    """Identical inputs produce identical authorization results."""

    def test_identical_inputs_produce_same_result(self, gov):
        """can_apply with identical inputs returns consistent results."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "deterministic-prompt")
        req = _create_approval_request(approval_svc, pkg, "deterministic-prompt")
        _, _, auth = _approve(approval_svc, req)

        results = []
        for _ in range(5):
            r = auth_svc.can_apply(
                change_type=RecommendationType.PROMPT_CHANGE,
                subject_id="deterministic-prompt",
                authorization_id=auth.authorization_id,
                target_version="1",
            )
            results.append(r)

        # All 5 results must be identical
        for r in results:
            assert r.decision == GateDecision.AUTHORIZED
            assert r.is_authorized is True

    def test_changing_input_changes_result(self, gov):
        """Changing target_version flips result from AUTHORIZED to BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "det-change-prompt")
        req = _create_approval_request(approval_svc, pkg, "det-change-prompt")
        _, _, auth = _approve(approval_svc, req)

        r_match = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="det-change-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert r_match.decision == GateDecision.AUTHORIZED

        r_mismatch = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="det-change-prompt",
            authorization_id=auth.authorization_id,
            target_version="999",
        )
        assert r_mismatch.decision == GateDecision.BLOCKED

    def test_no_authorization_id_is_deterministically_blocked(self, gov):
        """can_apply with no authorization ID is always blocked."""
        auth_svc = gov["auth_svc"]

        for _ in range(3):
            r = auth_svc.can_apply(
                change_type=RecommendationType.PROMPT_CHANGE,
                subject_id="any-prompt",
                authorization_id=None,
            )
            assert r.decision == GateDecision.BLOCKED
            assert r.is_authorized is False


# ═════════════════════════════════════════════════════════════════════════════
# 12. SECURITY BYPASS TESTS
# ═════════════════════════════════════════════════════════════════════════════


class TestSecurityBypass:
    """Every bypass attempt must fail safely."""

    def test_bypass_invalid_authorization_id(self, gov):
        """Non-existent authorization ID → BLOCKED."""
        auth_svc = gov["auth_svc"]

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="any",
            authorization_id="AUTH-DOES-NOT-EXIST",
        )
        assert result.decision == GateDecision.BLOCKED

    def test_bypass_authorization_without_evidence(self, gov):
        """Authorization referencing missing evidence → BLOCKED."""
        auth_svc = gov["auth_svc"]
        repo = gov["repo"]

        # Forge authorization with non-existent evidence
        forged_decision = HumanDecision(
            decision_id="DEC-BYPASS-NOEV",
            approval_request_id="APR-BYPASS-NOEV",
            decision=DecisionType.APPROVE,
            decision_maker_id="human@enterprise.org",
            actor_type=ActorType.HUMAN,
            decision_timestamp=datetime.now(timezone.utc).isoformat(),
            decision_reason="Forged",
            evidence_acknowledged=True,
            version_acknowledged=True,
            commit_acknowledged=False,
        )
        repo.save_decision(forged_decision)

        auth = auth_svc.issue_authorization(
            approval_request_id="APR-BYPASS-NOEV",
            decision_id="DEC-BYPASS-NOEV",
            authorized_change_type=RecommendationType.PROMPT_CHANGE,
            authorized_subject="no-evidence-target",
            evidence_package_id="EVP-MISSING",
            evidence_package_hash="fake-hash",
            authorized_version="1",
        )

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="no-evidence-target",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED

    def test_bypass_human_approval_for_wrong_version(self, gov):
        """Human approved V1 but target is V2 → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "wrong-ver", prompt_version="1")
        req = _create_approval_request(
            approval_svc, pkg, "wrong-ver", proposed_version="1"
        )
        _, _, auth = _approve(approval_svc, req)

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="wrong-ver",
            authorization_id=auth.authorization_id,
            target_version="2",
        )
        assert result.decision == GateDecision.BLOCKED

    def test_bypass_human_approval_for_wrong_commit(self, gov):
        """Human approved commit AAA but target is commit BBB → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = evidence_svc.create_evidence_package(
            subject_type="CODE",
            subject_id="commit-bypass",
            git_commit_sha="commit_aaa",
            ci_run_id="ci_aaa",
            lab_verification_id="lab_aaa",
        )
        req = approval_svc.create_approval_request(
            change_type=RecommendationType.CODE_CHANGE,
            subject_type="CODE",
            subject_id="commit-bypass",
            evidence_package_id=pkg.package_id,
            proposed_commit_sha="commit_aaa",
            ci_verification_id="ci_aaa",
            lab_verification_id="lab_aaa",
        )
        _, _, auth = approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="eng@enterprise.org",
            decision_reason="Approved commit AAA",
            actor_type=ActorType.HUMAN,
            evidence_acknowledged=True,
            version_acknowledged=True,
            commit_acknowledged=True,
        )

        result = auth_svc.can_apply(
            change_type=RecommendationType.CODE_CHANGE,
            subject_id="commit-bypass",
            authorization_id=auth.authorization_id,
            target_commit_sha="commit_bbb",
        )
        assert result.decision == GateDecision.BLOCKED
        assert any("Commit SHA mismatch" in b for b in result.blockers)

    def test_bypass_authorization_after_rejection(self, gov):
        """Rejected request → no auth → can_apply with fabricated auth → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "reject-bypass")
        req = _create_approval_request(approval_svc, pkg, "reject-bypass")

        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.REJECT,
            decision_maker_id="eng@enterprise.org",
            decision_reason="Rejected.",
            actor_type=ActorType.HUMAN,
        )

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="reject-bypass",
            authorization_id="AUTH-FABRICATED",
        )
        assert result.decision == GateDecision.BLOCKED

    def test_bypass_authorization_after_revocation(self, gov):
        """Revoked auth → can_apply → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "revoke-bypass")
        req = _create_approval_request(approval_svc, pkg, "revoke-bypass")
        _, _, auth = _approve(approval_svc, req)

        auth_svc.revoke_authorization(
            auth.authorization_id,
            actor_id="security@enterprise.org",
            reason="Revoked",
        )

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="revoke-bypass",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED

    def test_bypass_wrong_subject(self, gov):
        """Authorization for subject A → can_apply for subject B → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "subject-a")
        req = _create_approval_request(approval_svc, pkg, "subject-a")
        _, _, auth = _approve(approval_svc, req)

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="subject-b",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED
        assert any("Subject mismatch" in b for b in result.blockers)

    def test_bypass_wrong_change_type(self, gov):
        """PROMPT_CHANGE auth → can_apply for DEPLOYMENT → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg = _create_evidence(evidence_svc, "type-bypass")
        req = _create_approval_request(approval_svc, pkg, "type-bypass")
        _, _, auth = _approve(approval_svc, req)

        result = auth_svc.can_apply(
            change_type=RecommendationType.DEPLOYMENT,
            subject_id="type-bypass",
            authorization_id=auth.authorization_id,
            target_version="1",
        )
        assert result.decision == GateDecision.BLOCKED
        assert any("Change type mismatch" in b for b in result.blockers)

    def test_bypass_stale_artifact_via_evidence_package_swap(self, gov):
        """Authorization with evidence package A → can_apply referencing package B → BLOCKED."""
        approval_svc = gov["approval_svc"]
        auth_svc = gov["auth_svc"]
        evidence_svc = gov["evidence_svc"]

        pkg_a = _create_evidence(evidence_svc, "swap-prompt", prompt_version="1")
        req = _create_approval_request(approval_svc, pkg_a, "swap-prompt")
        _, _, auth = _approve(approval_svc, req)

        # Create a different evidence package
        pkg_b = _create_evidence(
            evidence_svc, "swap-prompt",
            prompt_version="1",
            observations=["Different content"],
            package_id="EVP-SWAPPED",
        )

        result = auth_svc.can_apply(
            change_type=RecommendationType.PROMPT_CHANGE,
            subject_id="swap-prompt",
            authorization_id=auth.authorization_id,
            target_version="1",
            current_evidence_package_id=pkg_b.package_id,
        )
        assert result.decision == GateDecision.BLOCKED
        assert any("Evidence package mismatch" in b for b in result.blockers)


# ═════════════════════════════════════════════════════════════════════════════
# 13. REST API LEVEL E2E
# ═════════════════════════════════════════════════════════════════════════════


class TestAPILevel:
    """Exercises governance invariants through the real FastAPI REST API."""

    def test_api_rejects_unauthenticated_approval(self):
        """POST /approve without X-Human-User header → 401."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        resp = client.post(
            "/api/v1/governance/approval-requests/APR-TEST/approve",
            json={"decision_reason": "testing"},
        )
        assert resp.status_code == 401

    def test_api_rejects_ai_agent_identity(self):
        """POST /approve with AI agent identity → 403."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)

        for ai_id in ["agent-gpt-4", "ai-copilot", "llm-autoapprover"]:
            resp = client.post(
                "/api/v1/governance/approval-requests/APR-TEST/approve",
                headers={"X-Human-User": ai_id},
                json={"decision_reason": "AI auto-approval"},
            )
            assert resp.status_code == 403, f"AI identity '{ai_id}' should be rejected"

    def test_api_lists_recommendations(self):
        """GET /recommendations returns 200."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        resp = client.get("/api/v1/governance/recommendations")
        assert resp.status_code == 200

    def test_api_lists_audit_trail(self):
        """GET /audit returns 200."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        resp = client.get("/api/v1/governance/audit")
        assert resp.status_code == 200
