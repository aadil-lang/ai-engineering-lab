import os
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
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService, redact_secrets
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.errors import (
    ApprovalRequestImmutableError,
    InvalidApprovalStateTransitionError,
    HumanIdentityRequiredError,
    AIAgentCannotApproveError,
    EvidencePackageTamperedError,
    AuthorizationExpiredError,
    AuthorizationRevokedError,
    PolicyViolationError,
    ConsequentialChangeBlockedError,
)


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_governance.db")
    return db_file


@pytest.fixture
def gov_stack(temp_db):
    repo = GovernanceRepository(db_path=temp_db)
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


def test_evidence_package_hashing_and_redaction(gov_stack):
    evidence_svc = gov_stack["evidence_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="customer-support",
        prompt_version="18",
        observations=["User query processed with ghp_12345678901234567890 secret token."],
        failures=["Missing priority field"],
        evaluation_snapshot_id="eval_snap_001",
    )

    assert pkg.package_id.startswith("EVP-")
    assert "[REDACTED_SECRET]" in pkg.observations[0]
    assert "ghp_" not in pkg.observations[0]
    assert len(pkg.content_hash) == 64  # SHA-256

    # Verify integrity
    assert evidence_svc.verify_package_integrity(pkg) is True


def test_evidence_package_tamper_detection(gov_stack):
    repo = gov_stack["repo"]
    evidence_svc = gov_stack["evidence_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="sentiment-classifier",
        prompt_version="1",
        observations=["Baseline test run passed."],
        evaluation_snapshot_id="eval_snap_base",
    )

    # Directly mutate content in DB
    with repo._get_connection() as conn:
        conn.execute(
            "UPDATE evidence_packages SET observations = ? WHERE package_id = ?",
            ('["TAMPERED OBSERVATION"]', pkg.package_id),
        )
        conn.commit()

    with pytest.raises(EvidencePackageTamperedError):
        evidence_svc.get_evidence_package(pkg.package_id)


def test_policy_effective_risk_determination(gov_stack):
    policy_svc = gov_stack["policy_svc"]

    # AI proposes LOW risk for a DEPLOYMENT -> Policy elevates to CRITICAL
    effective_deploy = policy_svc.determine_effective_risk(
        change_type=RecommendationType.DEPLOYMENT,
        ai_proposed_risk=RiskLevel.LOW,
    )
    assert effective_deploy == RiskLevel.CRITICAL

    # AI proposes LOW risk for PROMPT_CHANGE -> Policy elevates to HIGH
    effective_prompt = policy_svc.determine_effective_risk(
        change_type=RecommendationType.PROMPT_CHANGE,
        ai_proposed_risk=RiskLevel.LOW,
    )
    assert effective_prompt == RiskLevel.HIGH

    # AI proposes CRITICAL for PROMPT_CHANGE -> Preserves CRITICAL
    effective_critical = policy_svc.determine_effective_risk(
        change_type=RecommendationType.PROMPT_CHANGE,
        ai_proposed_risk=RiskLevel.CRITICAL,
    )
    assert effective_critical == RiskLevel.CRITICAL


def test_approval_request_immutability(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    repo = gov_stack["repo"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="incident-triage",
        prompt_version="2",
        evaluation_snapshot_id="eval_snap_triage",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="incident-triage",
        proposed_version="2",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_triage",
    )

    assert req.status == ApprovalRequestStatus.PENDING

    # Attempting to mutate subject or version in repository must raise error
    req.proposed_version = "3"
    with pytest.raises(ApprovalRequestImmutableError):
        repo.save_approval_request(req)


def test_ai_agent_cannot_approve_change(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="fraud-detector",
        prompt_version="5",
        evaluation_snapshot_id="eval_snap_fraud",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="fraud-detector",
        proposed_version="5",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_fraud",
    )

    # 1. Non-human ActorType must fail
    with pytest.raises(AIAgentCannotApproveError):
        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="agent-claude-3",
            decision_reason="Evaluation score is 99%",
            actor_type=ActorType.AI_AGENT,
            evidence_acknowledged=True,
            version_acknowledged=True,
        )

    # 2. Spoofed human with AI ID prefix must fail
    with pytest.raises(AIAgentCannotApproveError):
        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="ai-copilot",
            decision_reason="Autonomous approval",
            actor_type=ActorType.HUMAN,
            evidence_acknowledged=True,
            version_acknowledged=True,
        )

    # 3. Blank identity must fail
    with pytest.raises(HumanIdentityRequiredError):
        approval_svc.record_decision(
            approval_request_id=req.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="",
            decision_reason="No identity provided",
            actor_type=ActorType.HUMAN,
            evidence_acknowledged=True,
            version_acknowledged=True,
        )


def test_human_approval_issues_scoped_authorization(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    auth_svc = gov_stack["auth_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="intent-classifier",
        prompt_version="18",
        evaluation_snapshot_id="eval_snap_18",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="intent-classifier",
        proposed_version="18",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_18",
    )

    apr, dec, auth = approval_svc.record_decision(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="eng_alice@company.com",
        decision_reason="Frozen evaluation regression tests confirmed 0 regressions and 99% accuracy.",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        authorization_scope="PROMOTE",
    )

    assert apr.status == ApprovalRequestStatus.APPROVED
    assert dec.decision == DecisionType.APPROVE
    assert auth is not None
    assert auth.status == AuthorizationStatus.ACTIVE
    assert auth.authorized_version == "18"
    assert auth.authorized_subject == "intent-classifier"

    # Test can_apply for authorized version
    result = auth_svc.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="intent-classifier",
        authorization_id=auth.authorization_id,
        target_version="18",
        requested_scope="PROMOTE",
    )
    assert result.decision == GateDecision.AUTHORIZED
    assert result.is_authorized is True
    assert len(result.blockers) == 0


def test_authorization_version_specificity_blocks_v19(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    auth_svc = gov_stack["auth_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="intent-classifier",
        prompt_version="18",
        evaluation_snapshot_id="eval_snap_18",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="intent-classifier",
        proposed_version="18",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_18",
    )

    _, _, auth = approval_svc.record_decision(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="eng_bob@company.com",
        decision_reason="Approved v18 only",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
    )

    # Attempt to apply v18 approval to v19 MUST BE BLOCKED
    check_v19 = auth_svc.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="intent-classifier",
        authorization_id=auth.authorization_id,
        target_version="19",
    )
    assert check_v19.decision == GateDecision.BLOCKED
    assert check_v19.is_authorized is False
    assert any("Version mismatch" in b for b in check_v19.blockers)


def test_authorization_commit_sha_specificity_blocks_stale_commit(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    auth_svc = gov_stack["auth_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="CODE",
        subject_id="core-service",
        git_commit_sha="abc1234567890",
        ci_run_id="ci_run_999",
        lab_verification_id="lab_verif_999",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.CODE_CHANGE,
        subject_type="CODE",
        subject_id="core-service",
        proposed_commit_sha="abc1234567890",
        evidence_package_id=pkg.package_id,
        ci_verification_id="ci_run_999",
        lab_verification_id="lab_verif_999",
    )

    _, _, auth = approval_svc.record_decision(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="eng_carol@company.com",
        decision_reason="Approved PR commit abc1234567890",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        commit_acknowledged=True,
    )

    # Commit abc1234567890 is authorized
    check_ok = auth_svc.can_apply(
        change_type=RecommendationType.CODE_CHANGE,
        subject_id="core-service",
        authorization_id=auth.authorization_id,
        target_commit_sha="abc1234567890",
    )
    assert check_ok.is_authorized is True

    # New commit def987 arrives on PR -> Old authorization is BLOCKED
    check_stale = auth_svc.can_apply(
        change_type=RecommendationType.CODE_CHANGE,
        subject_id="core-service",
        authorization_id=auth.authorization_id,
        target_commit_sha="def9876543210",
    )
    assert check_stale.decision == GateDecision.BLOCKED
    assert check_stale.is_authorized is False
    assert any("Commit SHA mismatch" in b for b in check_stale.blockers)


def test_revoked_authorization_is_blocked(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    auth_svc = gov_stack["auth_svc"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="summary-agent",
        prompt_version="3",
        evaluation_snapshot_id="eval_snap_3",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="summary-agent",
        proposed_version="3",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_3",
    )

    _, _, auth = approval_svc.record_decision(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="eng_david@company.com",
        decision_reason="Initial approval",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
    )

    # Revoke
    revoked = auth_svc.revoke_authorization(
        authorization_id=auth.authorization_id,
        actor_id="security_officer",
        reason="Security flaw found post-approval.",
    )
    assert revoked.status == AuthorizationStatus.REVOKED

    # can_apply must return BLOCKED
    check = auth_svc.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="summary-agent",
        authorization_id=auth.authorization_id,
        target_version="3",
    )
    assert check.decision == GateDecision.BLOCKED
    assert check.is_authorized is False
    assert any("REVOKED" in b for b in check.blockers)


def test_immutable_audit_trail_recorded(gov_stack):
    approval_svc = gov_stack["approval_svc"]
    evidence_svc = gov_stack["evidence_svc"]
    repo = gov_stack["repo"]

    pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="audited-prompt",
        prompt_version="1",
        evaluation_snapshot_id="eval_snap_audit",
    )

    req = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="audited-prompt",
        proposed_version="1",
        evidence_package_id=pkg.package_id,
        evaluation_snapshot_id="eval_snap_audit",
    )

    approval_svc.record_decision(
        approval_request_id=req.approval_request_id,
        decision=DecisionType.REJECT,
        decision_maker_id="eng_reviewer@company.com",
        decision_reason="Insufficient unit test coverage.",
        actor_type=ActorType.HUMAN,
    )

    audit_records = repo.list_audit_records(subject_id="audited-prompt")
    assert len(audit_records) >= 2
    event_types = [a.event_type for a in audit_records]
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_REJECTED" in event_types

    # Ensure content hashes exist on all records
    for rec in audit_records:
        assert len(rec.content_hash) == 64
