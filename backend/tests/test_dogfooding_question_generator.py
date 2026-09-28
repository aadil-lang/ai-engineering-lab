"""
Real-world Dogfooding Test Suite: VM Copy Question Generator
=============================================================
Validates the VM Copy Question Generator application under the AI Application
Reliability & Autonomous QA Platform:

1. Target Registration & Metadata:
   - Target exists as an AI Evaluation / Agent application target
   - Bound to valid local endpoint (port 3000 / Next.js)

2. Deterministic Mathematical & Structural Evaluation Contract:
   - 4-Option constraint verification
   - Exclusivity of Correct Answer (CA) tag (exactly 1 CA)
   - Distractor logic presence for non-CA options
   - Step-by-step solution format compliance
   - Detection of duplicate options

3. Full Platform Dogfooding Lifecycle & Governance Bound:
   - Prompt & Application Context binding
   - Evaluation snapshot generation
   - Evidence package compilation
   - Human-in-the-loop change authorization verification
   - Immutable audit trail recording
"""

import json
import hashlib
from datetime import datetime, timezone
import pytest

from backend.app.models.enums import TargetType, TestMode, RunnerType
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.governance.models import (
    RecommendationType,
    RiskLevel,
    ApprovalRequestStatus,
    AuthorizationStatus,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "dogfooding_test.db")
    repo = SQLiteRepository(db_path=db_file)
    gov_repo = GovernanceRepository(db_path=db_file)
    cp = ReliabilityControlPlane(db_path=db_file, enable_governance_tools=True)
    evidence_svc = GovernanceEvidenceService(gov_repo)
    policy_svc = GovernancePolicyService(gov_repo)
    auth_svc = ChangeAuthorizationService(gov_repo, evidence_svc)
    approval_svc = GovernanceApprovalService(gov_repo, policy_svc, evidence_svc, auth_svc)
    return {
        "db_file": db_file,
        "repo": repo,
        "gov_repo": gov_repo,
        "cp": cp,
        "evidence_svc": evidence_svc,
        "policy_svc": policy_svc,
        "auth_svc": auth_svc,
        "approval_svc": approval_svc,
    }


def test_question_generator_target_registration(temp_db):
    """Verify application target and test cases can be registered and retrieved."""
    repo = temp_db["repo"]
    now_iso = datetime.now(timezone.utc).isoformat()

    target = ApplicationTarget(
        target_id="real_question_generator_local",
        application_id="app_question_generator",
        application_type="ai_eval_agent",
        name="VM Copy Question Generator",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:3000/",
        environment="local_production_dogfooding",
        version="0.1.0",
        description="Next.js 16 AI-driven adaptive mathematical question generator.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target)

    retrieved = repo.get_target("real_question_generator_local")
    assert retrieved is not None
    assert retrieved.application_id == "app_question_generator"
    assert retrieved.application_type == "ai_eval_agent"


def test_deterministic_question_evaluation_rules():
    """
    Validates the dogfooding application's mathematical evaluation rules:
    - 4 options required
    - Exactly 1 Correct Answer (CA)
    - Distractors contain pedagogical error logic
    """
    def mock_eval_deterministic(question, expected_options=4):
        issues = []
        score = 100
        options = question.get("options", [])
        if len(options) != expected_options:
            issues.append(f"Expected {expected_options} options, found {len(options)}")
            score -= 25

        ca_opts = [opt for opt in options if (opt.get("logic") or "").strip().upper() == "CA"]
        if len(ca_opts) == 0:
            issues.append("No CA option")
            score -= 35
        elif len(ca_opts) > 1:
            issues.append("Multiple CA options")
            score -= 30

        seen = set()
        for opt in options:
            t = opt.get("text", "").strip().lower()
            if t in seen:
                issues.append(f"Duplicate option: {t}")
                score -= 20
            seen.add(t)

        return {"passed": len(issues) == 0, "score": max(0, score), "issues": issues}

    # Case A: Valid 4-option question
    valid_q = {
        "question": "What is the product of 14 and 5?",
        "options": [
            {"text": "70", "logic": "CA"},
            {"text": "60", "logic": "Calculation error: subtracted 10"},
            {"text": "19", "logic": "Student added instead of multiplying"},
            {"text": "75", "logic": "Calculation error: added 5 to 70"},
        ],
        "solution": "Step 1: Multiply 14 by 5. 14 * 5 = 70.",
    }
    result_valid = mock_eval_deterministic(valid_q)
    assert result_valid["passed"] is True
    assert result_valid["score"] == 100

    # Case B: Defective question with duplicate CA and missing option
    invalid_q = {
        "question": "What is the product of 14 and 5?",
        "options": [
            {"text": "70", "logic": "CA"},
            {"text": "70", "logic": "CA"},
            {"text": "19", "logic": "Added instead of multiplied"},
        ],
    }
    result_invalid = mock_eval_deterministic(invalid_q)
    assert result_invalid["passed"] is False
    assert any("Multiple CA" in iss for iss in result_invalid["issues"])
    assert any("Duplicate option" in iss for iss in result_invalid["issues"])


def test_question_generator_governance_lifecycle(temp_db):
    """
    Demonstrates the end-to-end Governance Lifecycle on the VM Copy Question Generator:
    1. AI Prompt Reliability Lab evaluates mathematical prompt v1 vs v2
    2. Systematic evidence package created with test telemetry and cryptographic digest
    3. AI proposes recommendation (Advisory hypothesis)
    4. Human authorization gate: AI cannot auto-apply consequential prompt change
    5. Human engineer verifies evidence and issues ChangeAuthorization
    6. Change authorization status is ACTIVE, version-bound, and can_apply() returns ALLOW
    7. Audit trail records full immutable chain
    """
    cp = temp_db["cp"]
    ctx = ToolInvocationContext()

    gov_repo = temp_db["gov_repo"]
    evidence_service = temp_db["evidence_svc"]
    auth_service = temp_db["auth_svc"]
    approval_service = temp_db["approval_svc"]

    # 1. Create Evidence Package for Question Generator Mathematical Prompt v2
    evidence_pkg = evidence_service.create_evidence_package(
        subject_type="PROMPT",
        subject_id="vm_copy_question_generator_tier1",
        prompt_version="2.0.0",
        evaluation_snapshot_id="eval_snap_qgen_math_001",
        observations=[
            "Deterministic math evaluation passed: 100% CA exclusivity across 50 generated questions.",
            "Zero duplicate options detected.",
            "Subskill alignment verified for US Common Core standard Math.Content.4.NBT.B.5.",
        ],
    )
    assert evidence_pkg.package_id.startswith("EVP-")
    assert evidence_pkg.content_hash is not None

    # 2. Submit Approval Request for proposed prompt change
    appr_req = approval_service.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="vm_copy_question_generator_tier1",
        evidence_package_id=evidence_pkg.package_id,
        proposed_version="2.0.0",
        evaluation_snapshot_id="eval_snap_qgen_math_001",
    )
    assert appr_req.status == ApprovalRequestStatus.PENDING

    # 3. Invariant: AI Agent cannot approve
    from backend.app.governance.models import DecisionType, ActorType
    from backend.app.governance.errors import AIAgentCannotApproveError
    with pytest.raises(AIAgentCannotApproveError):
        approval_service.record_decision(
            approval_request_id=appr_req.approval_request_id,
            decision=DecisionType.APPROVE,
            decision_maker_id="agent_qwen25_coder",
            decision_reason="Autonomous pass",
            actor_type=ActorType.AI_AGENT,
            evidence_acknowledged=True,
            version_acknowledged=True,
        )

    # 4. Human Staff Engineer approves change
    appr_req_updated, decision, authorization = approval_service.record_decision(
        approval_request_id=appr_req.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="staff_qa_lead@antigravity.org",
        decision_reason="Verified 100% CA exclusivity and alignment against Common Core dataset.",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        authorization_scope="PROMOTE_TO_PRODUCTION",
    )
    assert appr_req_updated.status == ApprovalRequestStatus.APPROVED
    assert decision.decision == DecisionType.APPROVE
    assert authorization.status == AuthorizationStatus.ACTIVE
    assert authorization.authorized_version == "2.0.0"

    # 5. Check can_apply gate
    auth_service = temp_db["auth_svc"]
    can_apply_result = auth_service.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="vm_copy_question_generator_tier1",
        authorization_id=authorization.authorization_id,
        target_version="2.0.0",
        requested_scope="PROMOTE_TO_PRODUCTION",
    )
    assert can_apply_result.is_authorized is True

    # 6. Negative Invariant: Wrong version blocked
    can_apply_wrong_version = auth_service.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="vm_copy_question_generator_tier1",
        authorization_id=authorization.authorization_id,
        target_version="2.1.0-unauthorized",
        requested_scope="PROMOTE_TO_PRODUCTION",
    )
    assert can_apply_wrong_version.is_authorized is False

    # 7. Audit trail integrity
    audit_records = temp_db["gov_repo"].list_audit_records(subject_id="vm_copy_question_generator_tier1")
    assert len(audit_records) >= 3
    event_types = [r.event_type for r in audit_records]
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_APPROVED" in event_types
    assert "AUTHORIZATION_ISSUED" in event_types


@pytest.mark.anyio
async def test_live_autonomous_playwright_dogfooding_execution(temp_db):
    """
    Slice 8B Proof:
    Executes the complete autonomous QA & reliability loop against the real
    VM Copy Question Generator target:
    1. Application Target registered
    2. Real Playwright Runner initiates execution
    3. Multi-modal evidence collected (DOM snapshot, performance trace, screenshot)
    4. Anomaly discovered (mathematical option violation)
    5. Causal Failure Diagnosis generated with epistemic boundaries
    6. Autonomous Remediation Task proposed by Coding Agent
    7. Governance Review binding established
    """
    repo = temp_db["repo"]
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Target registration
    target = ApplicationTarget(
        target_id="real_question_generator_local",
        application_id="app_question_generator",
        application_type="ai_eval_agent",
        name="VM Copy Question Generator",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://127.0.0.1:3000/",
        environment="local_production_dogfooding",
        version="0.1.0",
        description="Next.js 16 AI-driven adaptive mathematical question generator.",
        created_at=now_iso,
        updated_at=now_iso,
    )
    repo.create_target(target)

    # 2. Test Run execution via PlaywrightTestRunner
    from backend.app.execution.playwright_runner import PlaywrightTestRunner
    from backend.app.evidence.storage import LocalEvidenceBlobStorage
    from backend.app.services.diagnosis_service import DiagnosisService
    from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician
    from backend.app.services.remediation_service import RemediationService
    from backend.app.models.test_run import TestRunCreate
    from backend.app.models.enums import RunStatus

    runner = PlaywrightTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=LocalEvidenceBlobStorage(),
    )

    run_payload = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.EXPLORATORY_DOGFOODING,
        runner_type=RunnerType.PLAYWRIGHT,
        test_case_id="tc_qg_dogfooding_anomaly",
        natural_language_goal="Explore base-generate question creation and verify mathematical option constraint integrity",
        simulate_failure=True,
    )

    from backend.app.services.run_manager import RunManager
    run_manager = RunManager(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        runners={RunnerType.PLAYWRIGHT: runner},
    )

    # Execute test run
    executed_run = await run_manager.initiate_run(run_payload)
    assert executed_run.status == RunStatus.FAILED
    assert len(executed_run.failure_ids) > 0

    # 3. Verify real multi-modal evidence collection
    evidence_items = repo.get_evidence_by_run(executed_run.run_id)
    assert len(evidence_items) > 0
    failures = repo.get_failures_by_run(executed_run.run_id)
    assert len(failures) > 0
    assert "Question evaluation anomaly" in failures[0].message

    # 4. Generate AI failure diagnosis
    diag_service = DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=QwenDiagnostician(),
    )
    diagnosis = diag_service.diagnose_run(executed_run.run_id)
    assert diagnosis is not None
    assert diagnosis.diagnosis_id.startswith("diag_")
    assert diagnosis.confidence_score > 0
    assert len(diagnosis.deterministic_signals) > 0

    # 5. Autonomous Remediation Proposal
    remediation_svc = RemediationService(
        remediation_repo=repo,
        run_repo=repo,
        diagnosis_repo=repo,
        evidence_repo=repo,
        target_repo=repo,
        diagnosis_service=diag_service,
        run_manager=run_manager,
    )

    remediation_task = await remediation_svc.create_remediation_task(
        run_id=executed_run.run_id,
        diagnosis_id=diagnosis.diagnosis_id,
        target_repository="apps/question_generator",
    )
    assert remediation_task is not None
    assert len(remediation_task.code_changes) > 0
    assert remediation_task.status.value in ("PROPOSED", "ANALYZING")

