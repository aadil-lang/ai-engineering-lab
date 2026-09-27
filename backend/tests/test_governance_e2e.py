import os
import pytest
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    EvaluationSuite,
    EvaluationCase,
    EvaluationStrategy,
    EvaluationCategory,
    EvaluationStatus,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.prompt_service import PromptService
from backend.app.prompt_lab.evaluation_service import EvaluationService
from backend.app.prompt_lab.diagnosis_service import PromptDiagnosisService
from backend.app.prompt_lab.evaluator_service import JSONSchemaEvaluator, RuleBasedEvaluator

from backend.app.governance.models import (
    RecommendationType,
    ApprovalRequestStatus,
    HumanDecision,
    ChangeAuthorization,
    AuthorizationStatus,
    DecisionType,
    ActorType,
    GateDecision,
    RiskLevel,
)
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.evidence_service import GovernanceEvidenceService
from backend.app.governance.policy_service import GovernancePolicyService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.errors import (
    ConsequentialChangeBlockedError,
    EvidencePackageTamperedError,
)


@pytest.fixture
def test_environment(tmp_path):
    pl_db = str(tmp_path / "prompt_lab.db")
    gov_db = str(tmp_path / "governance.db")

    prompt_repo = PromptLabRepository(db_path=pl_db)
    prompt_svc = PromptService(prompt_repo)
    eval_svc = EvaluationService(prompt_repo, prompt_svc)
    diag_svc = PromptDiagnosisService()

    gov_repo = GovernanceRepository(db_path=gov_db)
    evidence_svc = GovernanceEvidenceService(gov_repo)
    policy_svc = GovernancePolicyService(gov_repo)
    auth_svc = ChangeAuthorizationService(gov_repo, evidence_svc)
    approval_svc = GovernanceApprovalService(gov_repo, policy_svc, evidence_svc, auth_svc)

    return {
        "prompt_repo": prompt_repo,
        "prompt_svc": prompt_svc,
        "eval_svc": eval_svc,
        "diag_svc": diag_svc,
        "gov_repo": gov_repo,
        "evidence_svc": evidence_svc,
        "policy_svc": policy_svc,
        "auth_svc": auth_svc,
        "approval_svc": approval_svc,
    }


def test_23_step_prompt_governance_remediation_lifecycle(test_environment):
    """
    Executes the comprehensive 23-step Prompt Governance & Remediation scenario:
    Proves that consequential prompt promotion is strictly blocked without valid,
    artifact-bound human authorization, and survives neither version changes nor evidence mutation.
    """
    prompt_svc = test_environment["prompt_svc"]
    prompt_repo = test_environment["prompt_repo"]
    eval_svc = test_environment["eval_svc"]
    diag_svc = test_environment["diag_svc"]
    evidence_svc = test_environment["evidence_svc"]
    auth_svc = test_environment["auth_svc"]
    approval_svc = test_environment["approval_svc"]
    gov_repo = test_environment["gov_repo"]

    # Step 1: Prompt v1 exists
    p_def = prompt_svc.create_prompt(
        prompt_id="incident-classifier",
        name="Incident Severity Classifier",
        description="Classifies technical incidents into structured JSON.",
    )
    # v1 is flawed (outputs unstructured plain text)
    v1 = prompt_svc.create_prompt_version(
        prompt_id="incident-classifier",
        template="Incident description: {{description}}. Output severity: HIGH.",
        variables_schema={"required": ["description"]},
        output_schema={"type": "object", "required": ["severity"]},
        change_reason="Initial baseline version",
    )
    assert v1.version == 1

    # Step 2: Evaluation Suite exists & frozen
    suite = eval_svc.create_suite(
        suite_id="suite-incident-v1",
        name="Incident Severity Evaluation Suite",
        description="Verifies incident classification schema compliance",
    )
    case_1 = EvaluationCase(
        case_id="case-db-down",
        input={"description": "Database connection pool exhausted"},
        expected_behavior="Valid JSON with severity HIGH",
        constraints=["valid_json"],
        evaluation_strategy=EvaluationStrategy.JSON_SCHEMA,
        severity="CRITICAL",
        tags=["database", "critical"],
    )
    eval_svc.create_suite_version(
        suite_id="suite-incident-v1",
        cases=[case_1],
        description="Frozen Suite v1",
        is_frozen=True,
    )

    # Step 3: Run v1 evaluation -> identifies failure
    run_v1 = eval_svc.execute_evaluation(
        prompt_id="incident-classifier",
        prompt_version=1,
        suite_id="suite-incident-v1",
        suite_version=1,
        model="gemini-1.5-pro",
        model_runner=lambda rendered, case: "Severity: HIGH (unstructured)",
    )
    assert run_v1.failed_cases == 1
    v1_case_result = run_v1.case_results[0]
    assert v1_case_result.overall_status == EvaluationStatus.FAIL

    # Step 4: Diagnosis identifies PROMPT_DEFECT
    assert len(run_v1.diagnoses) == 1
    diag = run_v1.diagnoses[0]
    from backend.app.prompt_lab.models import FailureCause
    assert diag.primary_cause in {FailureCause.PROMPT_DEFECT, FailureCause.SCHEMA_FAILURE, FailureCause.PARSER_FAILURE}

    # Step 5: Candidate v2 is formulated and evaluated against the frozen suite
    cand_v2 = diag_svc.formulate_improvement_candidate(
        source_prompt_version=1,
        diagnoses=run_v1.diagnoses,
        current_template=v1.template,
    )
    prompt_repo.save_candidate(cand_v2)

    v2 = prompt_svc.create_prompt_version(
        prompt_id="incident-classifier",
        template='Analyze incident: {{description}}. Return JSON: {"severity": "HIGH"}',
        variables_schema={"required": ["description"]},
        output_schema={"type": "object", "required": ["severity"]},
        change_reason=cand_v2.rationale,
        parent_version=1,
    )
    assert v2.version == 2

    # Step 6: v2 is evaluated against identical frozen suite -> Regression analysis passes
    run_v2 = eval_svc.execute_evaluation(
        prompt_id="incident-classifier",
        prompt_version=2,
        suite_id="suite-incident-v1",
        suite_version=1,
        model="gemini-1.5-pro",
        model_runner=lambda rendered, case: '{"severity": "HIGH"}',
    )
    assert run_v2.passed_cases == 1
    assert run_v2.failed_cases == 0

    comparison = eval_svc.compare_prompt_versions(
        prompt_id="incident-classifier",
        v1_version=1,
        v2_version=2,
        suite_id="suite-incident-v1",
        suite_version=1,
    )
    assert comparison.fixed_failures_count == 1
    assert comparison.regressions_count == 0

    # Step 7: Create evaluation snapshot & Evidence Package
    snap_v2 = eval_svc.create_evaluation_snapshot(run_v2)
    evidence_pkg = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="incident-classifier",
        prompt_version="2",
        evaluation_snapshot_id=snap_v2.snapshot_id,
        observations=["All 1 test cases in frozen suite passed JSON schema validation."],
        verification_results={"pass_rate": 1.0, "regressions": 0},
    )

    # Step 8: Governance recommendation is generated
    rec = approval_svc.create_recommendation(
        recommendation_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="incident-classifier",
        source_system="PROMPT_LAB",
        proposed_action="Promote Prompt v2 to production",
        rationale="Fixed schema defect with zero regressions on frozen evaluation suite.",
        source_evaluation_id=run_v2.evaluation_run_id,
        source_diagnosis_id=diag.diagnosis_id,
        source_evidence_ids=[evidence_pkg.package_id],
        risk_level=RiskLevel.MEDIUM,
    )
    assert rec.effective_risk == RiskLevel.HIGH  # Governance policy bounds PROMPT_CHANGE to HIGH minimum

    # Step 9: Approval request is created
    apr = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="incident-classifier",
        evidence_package_id=evidence_pkg.package_id,
        recommendation_id=rec.recommendation_id,
        current_version="1",
        proposed_version="2",
        evaluation_snapshot_id=snap_v2.snapshot_id,
    )
    assert apr.status == ApprovalRequestStatus.PENDING

    # Step 10 & 11: No human decision exists -> Attempting promotion MUST BE BLOCKED
    with pytest.raises(ConsequentialChangeBlockedError):
        prompt_svc.promote_prompt_version(
            prompt_id="incident-classifier",
            version=2,
            authorization_id="NON_EXISTENT_AUTH",
            auth_service=auth_svc,
        )

    # Step 12: Human approves v2
    apr_approved, decision, auth = approval_svc.record_decision(
        approval_request_id=apr.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="lead_ai_engineer@enterprise.org",
        decision_reason="Verified evaluation snapshot and regression matrix showing 0 regressions.",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        authorization_scope="PROMOTE",
    )
    assert apr_approved.status == ApprovalRequestStatus.APPROVED
    assert auth is not None
    assert auth.authorized_version == "2"

    # Step 13, 14 & 15: Change authorization is used specifically for v2 -> Promotion succeeds
    promoted_v2 = prompt_svc.promote_prompt_version(
        prompt_id="incident-classifier",
        version=2,
        authorization_id=auth.authorization_id,
        auth_service=auth_svc,
    )
    assert promoted_v2.status == PromptStatus.DEPLOYED

    # Authorization is now marked as USED
    consumed_auth = auth_svc.get_authorization(auth.authorization_id)
    assert consumed_auth.status == AuthorizationStatus.USED

    # Step 16 & 17: Attempt to promote v3 using v2 authorization -> Promotion is BLOCKED
    # Create v3
    v3 = prompt_svc.create_prompt_version(
        prompt_id="incident-classifier",
        template='Analyze incident: {{description}}. Return JSON: {"severity": "HIGH", "confidence": 0.99}',
        variables_schema={"required": ["description"]},
        output_schema={"type": "object", "required": ["severity"]},
        change_reason="Unreviewed candidate v3",
    )
    assert v3.version == 3

    # Attempt promotion of v3 with v2 auth
    with pytest.raises(ConsequentialChangeBlockedError):
        prompt_svc.promote_prompt_version(
            prompt_id="incident-classifier",
            version=3,
            authorization_id=auth.authorization_id,
            auth_service=auth_svc,
        )

    # Step 18 & 19: Mutate evidence -> Existing authorization becomes invalid
    # Create fresh approval for a different scenario to test evidence tampering
    pkg_tamper = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="incident-classifier",
        prompt_version="2",
        evaluation_snapshot_id="snap_tamper",
    )
    apr_tamper = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="incident-classifier",
        evidence_package_id=pkg_tamper.package_id,
        proposed_version="2",
        evaluation_snapshot_id="snap_tamper",
    )
    _, _, auth_tamper = approval_svc.record_decision(
        approval_request_id=apr_tamper.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="lead_ai_engineer@enterprise.org",
        decision_reason="Approved prior to evidence mutation",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
    )
    # Directly tamper with evidence in DB
    with gov_repo._get_connection() as conn:
        conn.execute(
            "UPDATE evidence_packages SET observations = ? WHERE package_id = ?",
            ('["TAMPERED DATA"]', pkg_tamper.package_id),
        )
        conn.commit()

    check_tamper = auth_svc.can_apply(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_id="incident-classifier",
        authorization_id=auth_tamper.authorization_id,
        target_version="2",
    )
    assert check_tamper.decision == GateDecision.BLOCKED
    assert any("evidence package" in b.lower() for b in check_tamper.blockers)

    # Step 20, 21 & 22: Create fresh approval request, human rejects it -> Promotion remains BLOCKED
    pkg_fresh = evidence_svc.create_evidence_package(
        subject_type="PROMPT",
        subject_id="incident-classifier",
        prompt_version="3",
        evaluation_snapshot_id="snap_fresh",
    )
    apr_v3 = approval_svc.create_approval_request(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="incident-classifier",
        evidence_package_id=pkg_fresh.package_id,
        proposed_version="3",
        evaluation_snapshot_id="snap_fresh",
    )
    apr_rejected, dec_rejected, auth_rejected = approval_svc.record_decision(
        approval_request_id=apr_v3.approval_request_id,
        decision=DecisionType.REJECT,
        decision_maker_id="lead_ai_engineer@enterprise.org",
        decision_reason="Rejected v3 due to incomplete latency benchmarks.",
        actor_type=ActorType.HUMAN,
    )
    assert apr_rejected.status == ApprovalRequestStatus.REJECTED
    assert auth_rejected is None

    # Step 23: Audit trail contains the complete sequence
    audit_records = gov_repo.list_audit_records(subject_id="incident-classifier")
    event_types = [a.event_type for a in audit_records]
    assert "RECOMMENDATION_CREATED" in event_types
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_APPROVED" in event_types
    assert "AUTHORIZATION_ISSUED" in event_types
    assert "AUTHORIZATION_USED" in event_types
    assert "APPROVAL_REJECTED" in event_types


def test_git_lifecycle_stale_commit_invalidation(test_environment):
    """
    Verifies stale commit protection:
    Commit A -> PR -> CI -> Lab -> Approved -> Commit B arrives -> Old authorization is BLOCKED.
    """
    evidence_svc = test_environment["evidence_svc"]
    approval_svc = test_environment["approval_svc"]
    auth_svc = test_environment["auth_svc"]

    # Commit A evidence
    pkg_a = evidence_svc.create_evidence_package(
        subject_type="CODE",
        subject_id="billing-service",
        git_commit_sha="commit_aaa_111",
        ci_run_id="ci_run_aaa",
        lab_verification_id="lab_verif_aaa",
        observations=["All unit and integration tests passed for commit AAA."],
    )

    apr = approval_svc.create_approval_request(
        change_type=RecommendationType.CODE_CHANGE,
        subject_type="CODE",
        subject_id="billing-service",
        proposed_commit_sha="commit_aaa_111",
        evidence_package_id=pkg_a.package_id,
        ci_verification_id="ci_run_aaa",
        lab_verification_id="lab_verif_aaa",
    )

    _, _, auth_a = approval_svc.record_decision(
        approval_request_id=apr.approval_request_id,
        decision=DecisionType.APPROVE,
        decision_maker_id="tech_lead@enterprise.org",
        decision_reason="Approved Commit AAA after successful CI and Lab verification.",
        actor_type=ActorType.HUMAN,
        evidence_acknowledged=True,
        version_acknowledged=True,
        commit_acknowledged=True,
    )

    # Commit AAA is authorized
    check_a = auth_svc.can_apply(
        change_type=RecommendationType.CODE_CHANGE,
        subject_id="billing-service",
        authorization_id=auth_a.authorization_id,
        target_commit_sha="commit_aaa_111",
    )
    assert check_a.is_authorized is True

    # Commit BBB arrives on PR branch (new push)
    # Attempting to apply old authorization auth_a to Commit BBB MUST BE BLOCKED
    check_b = auth_svc.can_apply(
        change_type=RecommendationType.CODE_CHANGE,
        subject_id="billing-service",
        authorization_id=auth_a.authorization_id,
        target_commit_sha="commit_bbb_222",
    )
    assert check_b.decision == GateDecision.BLOCKED
    assert check_b.is_authorized is False
    assert any("Commit SHA mismatch" in b for b in check_b.blockers)
