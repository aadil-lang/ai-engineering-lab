import json
import pytest

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    EvaluationSuite,
    EvaluationSuiteVersion,
    EvaluationCase,
    EvaluationStrategy,
    EvaluationCategory,
    EvaluationStatus,
    SeverityLevel,
    FailureCause,
    CaseTransition,
    CandidateStatus,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.prompt_service import PromptService
from backend.app.prompt_lab.evaluation_service import EvaluationService
from backend.app.prompt_lab.diagnosis_service import PromptDiagnosisService


def test_prompt_lab_e2e_remediation_lifecycle():
    """
    End-to-End Controlled Integration Scenario:
    1. Create prompt v1
    2. Create evaluation suite
    3. Run v1
    4. Introduce controlled prompt defect (v1 fails on schema / constraints)
    5. Evaluation detects failure
    6. Evidence recorded
    7. Diagnosis generated
    8. Improvement candidate created
    9. Create prompt v2
    10. Run identical evaluation suite
    11. Detect fixed failures and regressions
    12. Compare v1/v2
    13. Preserve immutable evaluation snapshots
    14. Require human decision
    """
    repo = PromptLabRepository(db_path=":memory:")
    prompt_service = PromptService(repo)
    diagnosis_service = PromptDiagnosisService()
    eval_service = EvaluationService(repo, prompt_service, diagnosis_service)

    # 1. Create prompt definition
    prompt = prompt_service.create_prompt(
        prompt_id="prompt_order_triage",
        name="Order Exception Triage Prompt",
        description="Extracts incident severity, category, and action for order fulfillment issues.",
    )
    assert prompt.prompt_id == "prompt_order_triage"

    # Define common output schema
    order_output_schema = {
        "type": "object",
        "required": ["incident_category", "severity", "action_item"],
        "properties": {
            "incident_category": {"type": "string"},
            "severity": {"type": "string"},
            "action_item": {"type": "string"},
        },
    }

    # 2. Create versioned evaluation suite with diverse categories
    eval_service.create_suite(
        suite_id="suite_order_exceptions",
        name="Order Fulfillment Exception Test Suite",
        description="Comprehensive evaluation cases covering normal, boundary, missing info, and grounding.",
    )
    suite_cases = [
        EvaluationCase(
            case_id="case_normal_payment_timeout",
            category=EvaluationCategory.NORMAL,
            severity=SeverityLevel.HIGH,
            input={"issue": "Payment gateway timed out during charge capture for order 9871."},
            expected_behavior="Retry charge capture with secondary payment processor.",
            constraints=["forbidden: as an ai language model", "max_chars: 400"],
            evaluation_strategy=EvaluationStrategy.COMPOSITE,
        ),
        EvaluationCase(
            case_id="case_warehouse_shortage_grounding",
            category=EvaluationCategory.NORMAL,
            severity=SeverityLevel.CRITICAL,
            input={"issue": "Warehouse SKU 404 is out of stock in regional hub."},
            expected_behavior="Reroute order to alternate Hub B based on inventory manifest.",
            sources=[
                {"source_id": "hub_manifest", "content": "Regional hub A is depleted; Hub B has 500 units available for automatic reroute."}
            ],
            constraints=["forbidden: confidential", "citation_required"],
            evaluation_strategy=EvaluationStrategy.COMPOSITE,
        ),
        EvaluationCase(
            case_id="case_missing_order_number",
            category=EvaluationCategory.MISSING_INPUT,
            severity=SeverityLevel.MEDIUM,
            input={"issue": "Customer reported missing item but did not supply order ID."},
            expected_behavior="Prompt customer for missing order reference number.",
            constraints=["forbidden: internal error"],
            evaluation_strategy=EvaluationStrategy.COMPOSITE,
        ),
    ]

    suite_version = eval_service.create_suite_version(
        suite_id="suite_order_exceptions",
        cases=suite_cases,
        description="v1 frozen benchmark suite",
        is_frozen=False,
    )
    assert suite_version.version == 1

    # 3 & 4. Create prompt v1 with an intentional defect
    # Defect: Template omits instructions for required schema field 'action_item' and lacks grounding instructions.
    pv1 = prompt_service.create_prompt_version(
        prompt_id="prompt_order_triage",
        template="You are an order triage assistant. Read the issue: {{issue}}. Provide category and severity.",
        variables_schema={"required": ["issue"]},
        output_schema=order_output_schema,
        change_reason="Initial baseline implementation with unconstrained instructions.",
    )
    assert pv1.version == 1

    # Define mock model runner simulating v1's defective responses:
    # It omits 'action_item' on case 1, hallucinates without citations on case 2.
    def mock_runner_v1(rendered_prompt: str, case: EvaluationCase) -> str:
        if case.case_id == "case_normal_payment_timeout":
            # Defect: Missing required field 'action_item'
            return json.dumps({"incident_category": "payment_gateway", "severity": "HIGH"})
        elif case.case_id == "case_warehouse_shortage_grounding":
            # Defect: Missing citation and ungrounded claim
            return json.dumps({
                "incident_category": "inventory_depletion",
                "severity": "CRITICAL",
                "action_item": "Order drone delivery from extraterrestrial fulfillment center.",
            })
        else:
            return json.dumps({
                "incident_category": "customer_support",
                "severity": "MEDIUM",
                "action_item": "Prompt customer for order reference number.",
            })

    # 5 & 6. Run v1 evaluation against the frozen suite
    run_v1 = eval_service.execute_evaluation(
        prompt_id="prompt_order_triage",
        prompt_version=1,
        suite_id="suite_order_exceptions",
        suite_version=1,
        model="mock-agent-v1",
        model_runner=mock_runner_v1,
    )

    # Assert evaluation detected failures
    assert run_v1.total_cases == 3
    assert run_v1.failed_cases >= 2
    assert run_v1.pass_rate < 0.5

    # 7. Diagnoses generated
    assert len(run_v1.diagnoses) >= 2
    diag_schema = next(d for d in run_v1.diagnoses if d.case_id == "case_normal_payment_timeout")
    assert diag_schema.primary_cause in {FailureCause.PROMPT_DEFECT, FailureCause.SCHEMA_FAILURE}
    assert any(f.epistemic_type == "OBSERVED" for f in diag_schema.facts)
    assert any(f.epistemic_type == "INFERRED" for f in diag_schema.facts)
    assert any(f.epistemic_type == "HYPOTHESIS" for f in diag_schema.facts)

    # 8. Improvement candidate formulated (never auto-deploys)
    candidate = diagnosis_service.formulate_improvement_candidate(
        source_prompt_version=1,
        diagnoses=run_v1.diagnoses,
        current_template=pv1.template,
    )
    repo.save_candidate(candidate)
    assert candidate.status == CandidateStatus.PROPOSED
    assert "Formatting Constraint" in candidate.proposed_template or "Grounding Rule" in candidate.proposed_template

    # 9. Create prompt v2 based on diagnosis & candidate
    v2_template = (
        "You are an order triage assistant. Read the issue: {{issue}}.\n"
        "Return ONLY a JSON object with: incident_category, severity, and action_item.\n"
        "Rely strictly on provided context and include [Source: ...] citations when context is given."
    )
    pv2 = prompt_service.create_prompt_version(
        prompt_id="prompt_order_triage",
        template=v2_template,
        variables_schema={"required": ["issue"]},
        output_schema=order_output_schema,
        change_reason="Add explicit JSON schema constraint and strict source grounding instructions.",
        parent_version=1,
        status=PromptStatus.CANDIDATE,
    )
    assert pv2.version == 2

    # 10. Run identical evaluation suite against v2
    def mock_runner_v2(rendered_prompt: str, case: EvaluationCase) -> str:
        if case.case_id == "case_normal_payment_timeout":
            return json.dumps({
                "incident_category": "payment_gateway",
                "severity": "HIGH",
                "action_item": "Retry charge capture with secondary payment processor.",
            })
        elif case.case_id == "case_warehouse_shortage_grounding":
            return json.dumps({
                "incident_category": "inventory_depletion",
                "severity": "CRITICAL",
                "action_item": "Reroute order to Hub B with 500 units available [Source: hub_manifest].",
            })
        else:
            return json.dumps({
                "incident_category": "customer_support",
                "severity": "MEDIUM",
                "action_item": "Prompt customer for order reference number.",
            })

    run_v2 = eval_service.execute_evaluation(
        prompt_id="prompt_order_triage",
        prompt_version=2,
        suite_id="suite_order_exceptions",
        suite_version=1,
        model="mock-agent-v1",
        model_runner=mock_runner_v2,
    )
    assert run_v2.total_cases == 3
    assert run_v2.passed_cases == 3
    assert run_v2.pass_rate == 1.0

    # 11 & 12. Compare v1 and v2 on the same frozen suite
    comparison = eval_service.compare_prompt_versions(
        prompt_id="prompt_order_triage",
        v1_version=1,
        v2_version=2,
        suite_id="suite_order_exceptions",
        suite_version=1,
    )
    assert comparison.v1_pass_rate < 0.5
    assert comparison.v2_pass_rate == 1.0
    assert comparison.fixed_failures_count == 2
    assert comparison.regressions_count == 0
    assert comparison.pass_rate_delta > 0.5

    # 13. Verify immutable evaluation snapshots exist for both runs
    snap1 = repo.get_snapshot(f"eval_snap_prompt_order_triage_v1_suite_order_exceptions_v1")
    snap2 = repo.get_snapshot(f"eval_snap_prompt_order_triage_v2_suite_order_exceptions_v1")
    assert snap1 is not None and len(snap1.sha256_hash) == 64
    assert snap2 is not None and len(snap2.sha256_hash) == 64

    # 14. Human Decision: v2 is marked PASSED, but remains CANDIDATE until human approval
    assert pv2.status == PromptStatus.CANDIDATE
    # Candidate prompt is NOT automatically deployed
    all_versions = prompt_service.list_prompt_versions("prompt_order_triage")
    assert not any(v.status == PromptStatus.DEPLOYED for v in all_versions)
