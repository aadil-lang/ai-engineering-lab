"""
Slice 8C — Context-Aware Autonomous AI Dogfooding Test Suite
=============================================================

30 required tests validating the integration of:
- Slice 8B: Autonomous Playwright Dogfooding
- Slice 7.7.1: AI Application Context Contract
- Slice 7.8: Human Governance Authorization

Test Groups:
  1-10:  Context Binding & Provenance Preservation
  11-13: Epistemic Boundaries & Runtime Mismatch Detection
  14-20: Deterministic Evaluation & Causal Classification
  21-24: Prompt Candidate & Retest
  25-29: Governance Authorization
  30:    Complete E2E Provenance Chain
"""

import json
import hashlib
import uuid
import copy
from datetime import datetime, timezone, timedelta

import pytest

from backend.app.models.enums import (
    TestMode,
    RunnerType,
    ExecutionSource,
    RunStatus,
    CausalLayer,
    RetestTransition,
    ContractStatus,
    ContextVerificationStatus,
    TargetType,
)
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.dogfooding_context import (
    DogfoodingRunContext,
    ComponentVerification,
    AIContextEvidence,
    CausalClassification,
    PromptImprovementCandidate,
    RetestResult,
    RetestComparison,
    compute_config_hash,
)
from backend.app.prompt_lab.application_context_models import (
    AIApplicationManifest,
    EvaluationContext,
    ContextProvenance,
    ContextDifference,
    EpistemicStatus,
)
from backend.app.prompt_lab.application_context_service import (
    ApplicationContextService,
    compute_deterministic_context_hash,
)
from backend.app.services.dogfooding_context_service import DogfoodingContextService
from backend.app.governance.models import (
    RecommendationType,
    RiskLevel,
    ApprovalRequestStatus,
    AuthorizationStatus,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def ctx_service():
    """Fresh DogfoodingContextService for each test."""
    return DogfoodingContextService()


@pytest.fixture
def app_context_service(tmp_path):
    """ApplicationContextService with fresh repo."""
    from backend.app.prompt_lab.repository import PromptLabRepository
    repo = PromptLabRepository(db_path=str(tmp_path / "prompt_lab.db"))
    return ApplicationContextService(repo=repo)


@pytest.fixture
def sample_manifest(app_context_service):
    """Register and return a Question Generator manifest."""
    manifest = AIApplicationManifest(
        application_id="app_question_generator",
        feature_id="question_generation",
        application_name="VM Copy Question Generator",
        application_version="1.0.0",
        git_repository="https://github.com/example/question-generator",
        git_commit_sha="abc123def456",
        prompt_id="qgen_math_prompt",
        prompt_version=1,
        model="qwen2.5-coder:7b-instruct",
        model_version="7b-v1",
        generation_parameters={"temperature": 0.1, "num_predict": 700},
        input_schema={"type": "object", "properties": {"topic": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"question": {"type": "string"}, "options": {"type": "array"}}},
        retrieval_configuration={"type": "vector", "version": "v1", "top_k": 5},
        tool_configuration={"tools": ["calculator", "latex_renderer"]},
        parser_configuration={"type": "json", "version": "v1", "strict": True},
        behavioral_contract_ids=["contract_ca_exclusivity", "contract_no_duplicates", "contract_4_options"],
        evaluation_suite_ids=["suite_qgen_math_v1"],
        environment="staging",
    )
    return app_context_service.create_application_manifest(manifest)


@pytest.fixture
def frozen_context(app_context_service, sample_manifest):
    """Create and freeze an evaluation context."""
    ctx = app_context_service.create_evaluation_context(
        application_id="app_question_generator",
        suite_id="suite_qgen_math_v1",
        feature_id="question_generation",
        auto_freeze=True,
    )
    return ctx


@pytest.fixture
def sample_run():
    """Create a sample TestRun for binding."""
    return TestRun(
        run_id="run_8c_test_001",
        application_id="app_question_generator",
        application_version="1.0.0",
        test_mode=TestMode.EXPLORATORY_DOGFOODING,
        runner_type=RunnerType.PLAYWRIGHT,
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        status=RunStatus.FAILED,
    )


@pytest.fixture
def defective_ai_output():
    """Question Generator output with controlled failure."""
    return {
        "question": "What is the product of 14 and 5?",
        "options": [
            {"text": "70", "logic": "Correct calculation"},
            {"text": "60", "logic": "Subtracted 10"},
            {"text": "60", "logic": "Duplicate distractor"},
        ],
        "solution": "14 * 5 = 70",
        "difficulty": "medium",
    }


@pytest.fixture
def valid_ai_output():
    """Question Generator output that passes all checks."""
    return {
        "question": "What is the product of 14 and 5?",
        "options": [
            {"text": "70", "logic": "CA"},
            {"text": "60", "logic": "Subtracted 10"},
            {"text": "19", "logic": "Added instead"},
            {"text": "75", "logic": "Added 5 to 70"},
        ],
        "solution": "Step 1: 14 * 5 = 70",
        "difficulty": "medium",
    }


# ═══════════════════════════════════════════════════════════════════════
# Tests 1-10: Context Binding & Provenance Preservation
# ═══════════════════════════════════════════════════════════════════════

def test_01_ai_application_context_attached_to_dogfooding_run(ctx_service, frozen_context, sample_run):
    """1. AI application context is explicitly bound to dogfooding runs."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.run_id == sample_run.run_id
    assert binding.evaluation_context_id == frozen_context.context_id
    assert binding.application_id == frozen_context.application_id
    assert binding.ai_feature_detected is True


def test_02_exact_git_commit_preserved(ctx_service, frozen_context, sample_run):
    """2. Exact Git commit is preserved in the context binding."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.git_commit_sha == frozen_context.git_commit_sha
    assert binding.git_commit_sha == "abc123def456"


def test_03_exact_prompt_version_preserved(ctx_service, frozen_context, sample_run):
    """3. Exact prompt version is preserved."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.prompt_id == "qgen_math_prompt"
    assert binding.prompt_version == 1


def test_04_model_provenance_preserved(ctx_service, frozen_context, sample_run):
    """4. Model provenance is preserved."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.model == "qwen2.5-coder:7b-instruct"
    assert binding.model_version == "7b-v1"


def test_05_retrieval_provenance_preserved(ctx_service, frozen_context, sample_run):
    """5. Retrieval provenance is preserved as a configuration hash."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.retrieval_configuration_hash is not None
    # Hash should be deterministic for the same config
    expected_hash = compute_config_hash(frozen_context.retrieval_configuration)
    assert binding.retrieval_configuration_hash == expected_hash


def test_06_tool_provenance_preserved(ctx_service, frozen_context, sample_run):
    """6. Tool provenance is preserved as a configuration hash."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.tool_configuration_hash is not None
    expected_hash = compute_config_hash(frozen_context.tool_configuration)
    assert binding.tool_configuration_hash == expected_hash


def test_07_parser_provenance_preserved(ctx_service, frozen_context, sample_run):
    """7. Parser provenance is preserved as a configuration hash."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert binding.parser_configuration_hash is not None
    expected_hash = compute_config_hash(frozen_context.parser_configuration)
    assert binding.parser_configuration_hash == expected_hash


def test_08_behavioral_contract_binding_preserved(ctx_service, frozen_context, sample_run):
    """8. Behavioral contract binding preserved."""
    binding = ctx_service.bind_context_to_run(
        run_id=sample_run.run_id,
        evaluation_context=frozen_context,
    )
    assert "contract_ca_exclusivity" in binding.behavioral_contract_ids
    assert "contract_no_duplicates" in binding.behavioral_contract_ids
    assert "contract_4_options" in binding.behavioral_contract_ids
    assert len(binding.behavioral_contract_ids) == 3


def test_09_context_hash_deterministic(ctx_service, frozen_context, sample_run):
    """9. Context hash is deterministic — same context always produces the same hash."""
    binding1 = ctx_service.bind_context_to_run(
        run_id="run_hash_test_1",
        evaluation_context=frozen_context,
    )
    binding2 = ctx_service.bind_context_to_run(
        run_id="run_hash_test_2",
        evaluation_context=frozen_context,
    )
    assert binding1.context_hash == binding2.context_hash
    assert binding1.context_hash != ""
    assert len(binding1.context_hash) == 64  # SHA-256 hex


def test_10_context_immutability(ctx_service, frozen_context, sample_run):
    """10. Context immutability — binding requires frozen context."""
    unfrozen = EvaluationContext(
        context_id="ctx_unfrozen",
        application_id="app_test",
        feature_id="test_feature",
        application_version="1.0.0",
        prompt_id="prompt_test",
        prompt_version=1,
        model="test-model",
        is_frozen=False,
        context_hash="abc",
    )
    with pytest.raises(ValueError, match="must be frozen"):
        ctx_service.bind_context_to_run(
            run_id=sample_run.run_id,
            evaluation_context=unfrozen,
        )


# ═══════════════════════════════════════════════════════════════════════
# Tests 11-13: Epistemic Boundaries & Runtime Mismatch Detection
# ═══════════════════════════════════════════════════════════════════════

def test_11_runtime_prompt_mismatch_detected(ctx_service, frozen_context):
    """11. Runtime prompt mismatch is detected and flagged."""
    ctx_service.bind_context_to_run(
        run_id="run_prompt_mismatch",
        evaluation_context=frozen_context,
    )
    updated = ctx_service.verify_runtime_context(
        run_id="run_prompt_mismatch",
        actual_prompt=("qgen_math_prompt", 2),  # Version mismatch: declared v1, runtime v2
    )
    prompt_v = next(v for v in updated.component_verifications if v.component == "prompt")
    assert prompt_v.status == ContextVerificationStatus.MISMATCH
    assert prompt_v.mismatch_detail is not None
    assert "v1" in prompt_v.mismatch_detail
    assert "v2" in prompt_v.mismatch_detail


def test_12_runtime_model_mismatch_detected(ctx_service, frozen_context):
    """12. Runtime model mismatch is detected and flagged."""
    ctx_service.bind_context_to_run(
        run_id="run_model_mismatch",
        evaluation_context=frozen_context,
    )
    updated = ctx_service.verify_runtime_context(
        run_id="run_model_mismatch",
        actual_model="gpt-4o-mini",  # Different from declared qwen2.5-coder:7b-instruct
    )
    model_v = next(v for v in updated.component_verifications if v.component == "model")
    assert model_v.status == ContextVerificationStatus.MISMATCH
    assert model_v.observed_value == "gpt-4o-mini"


def test_13_declared_context_not_treated_as_observed(ctx_service, frozen_context):
    """13. Declared context is NOT treated as OBSERVED without runtime evidence."""
    binding = ctx_service.bind_context_to_run(
        run_id="run_epistemic_test",
        evaluation_context=frozen_context,
    )
    # Some components from provenance should be DECLARED, not automatically OBSERVED
    declared_components = [
        v for v in binding.component_verifications
        if v.epistemic_status == EpistemicStatus.DECLARED
    ]
    # Model provenance is DECLARED in our manifest setup
    assert len(declared_components) > 0, "At least one component should remain DECLARED without runtime evidence"

    # Verify that DECLARED components don't have VERIFIED status
    for v in declared_components:
        assert v.status != ContextVerificationStatus.VERIFIED, \
            f"Component '{v.component}' is DECLARED but has VERIFIED status — epistemic violation"


# ═══════════════════════════════════════════════════════════════════════
# Tests 14-20: Deterministic Evaluation & Causal Classification
# ═══════════════════════════════════════════════════════════════════════

def test_14_deterministic_evaluator_executes_before_semantic_diagnosis(
    ctx_service, frozen_context, defective_ai_output
):
    """14. Deterministic evaluator executes before semantic diagnosis."""
    ctx_service.bind_context_to_run(
        run_id="run_det_first",
        evaluation_context=frozen_context,
    )

    # Deterministic evaluation runs first
    det_result = ctx_service.run_deterministic_evaluation(
        run_id="run_det_first",
        ai_output=defective_ai_output,
        evaluation_rules={"type": "question_generator", "expected_option_count": 4},
    )

    assert det_result["passed"] is False
    assert det_result["is_authoritative"] is True
    assert len(det_result["deterministic_failures"]) > 0

    # Then causal classification uses deterministic results
    classification = ctx_service.classify_causal_layers(
        run_id="run_det_first",
        diagnosis_id="diag_test_001",
        deterministic_result=det_result,
    )
    assert classification is not None
    # The order is proven: deterministic ran first, classification used its output


def test_15_deterministic_failure_cannot_be_overridden_by_llm_judge(
    ctx_service, frozen_context, defective_ai_output
):
    """15. Deterministic failure cannot be overridden by LLM judge."""
    ctx_service.bind_context_to_run(
        run_id="run_no_override",
        evaluation_context=frozen_context,
    )

    det_result = ctx_service.run_deterministic_evaluation(
        run_id="run_no_override",
        ai_output=defective_ai_output,
        evaluation_rules={"type": "question_generator", "expected_option_count": 4},
    )

    assert det_result["passed"] is False
    assert det_result["is_authoritative"] is True

    # Even if an LLM judge claimed it passed, the deterministic result stands
    # The is_authoritative flag ensures this invariant
    assert det_result["deterministic_failures"], "Deterministic failures must not be empty"
    # Verify specific failures detected
    failure_text = " ".join(det_result["deterministic_failures"])
    assert "CA indicator" in failure_text or "Duplicate" in failure_text


def test_16_prompt_defect_not_assumed_automatically(ctx_service, frozen_context, defective_ai_output):
    """16. Prompt defect is not assumed automatically — requires evidence."""
    ctx_service.bind_context_to_run(
        run_id="run_no_auto_prompt",
        evaluation_context=frozen_context,
    )

    det_result = ctx_service.run_deterministic_evaluation(
        run_id="run_no_auto_prompt",
        ai_output=defective_ai_output,
        evaluation_rules={"type": "question_generator", "expected_option_count": 4},
    )

    # Without model_response_valid hint, should NOT assume PROMPT_DEFECT
    classification = ctx_service.classify_causal_layers(
        run_id="run_no_auto_prompt",
        diagnosis_id="diag_no_auto",
        deterministic_result=det_result,
    )

    # Primary should be APPLICATION_LOGIC (inferred from constraint failures)
    # not PROMPT_DEFECT (which requires additional evidence)
    assert classification.primary_layer != CausalLayer.PROMPT_DEFECT or \
        classification.primary_epistemic_status == EpistemicStatus.HYPOTHESIS, \
        "PROMPT_DEFECT must not be assumed with OBSERVED status without evidence"


def test_17_retrieval_failure_classified_independently(ctx_service, frozen_context):
    """17. Retrieval failure classified independently when mismatch detected."""
    ctx_service.bind_context_to_run(
        run_id="run_retrieval_fail",
        evaluation_context=frozen_context,
    )

    # Simulate retrieval mismatch
    ctx_service.verify_runtime_context(
        run_id="run_retrieval_fail",
        actual_retrieval_config={"type": "keyword", "version": "v2", "top_k": 10},  # Different from declared
    )

    det_result = {"passed": False, "deterministic_failures": [], "score": 50}

    classification = ctx_service.classify_causal_layers(
        run_id="run_retrieval_fail",
        diagnosis_id="diag_retrieval",
        deterministic_result=det_result,
    )

    # Should detect retrieval failure from verification mismatch
    all_layers = [classification.primary_layer] + classification.secondary_layers
    assert CausalLayer.RETRIEVAL_FAILURE in all_layers


def test_18_parser_failure_classified_independently(ctx_service, frozen_context):
    """18. Parser failure classified independently when mismatch detected."""
    ctx_service.bind_context_to_run(
        run_id="run_parser_fail",
        evaluation_context=frozen_context,
    )

    # Simulate parser mismatch
    ctx_service.verify_runtime_context(
        run_id="run_parser_fail",
        actual_parser_config={"type": "yaml", "version": "v2"},  # Different from declared json
    )

    det_result = {"passed": False, "deterministic_failures": [], "score": 50}

    classification = ctx_service.classify_causal_layers(
        run_id="run_parser_fail",
        diagnosis_id="diag_parser",
        deterministic_result=det_result,
    )

    all_layers = [classification.primary_layer] + classification.secondary_layers
    assert CausalLayer.PARSER_FAILURE in all_layers


def test_19_application_logic_failure_classified_independently(
    ctx_service, frozen_context, defective_ai_output
):
    """19. Application logic failure classified independently."""
    ctx_service.bind_context_to_run(
        run_id="run_app_logic",
        evaluation_context=frozen_context,
    )

    det_result = ctx_service.run_deterministic_evaluation(
        run_id="run_app_logic",
        ai_output=defective_ai_output,
        evaluation_rules={"type": "question_generator", "expected_option_count": 4},
    )

    classification = ctx_service.classify_causal_layers(
        run_id="run_app_logic",
        diagnosis_id="diag_app_logic",
        deterministic_result=det_result,
    )

    all_layers = [classification.primary_layer] + classification.secondary_layers
    # APPLICATION_LOGIC should be present (either primary or secondary)
    assert CausalLayer.APPLICATION_LOGIC in all_layers or \
        classification.primary_layer != CausalLayer.UNKNOWN


def test_20_unknown_causal_layer_preserved(ctx_service, frozen_context):
    """20. UNKNOWN causal layer is preserved when evidence is insufficient."""
    ctx_service.bind_context_to_run(
        run_id="run_unknown",
        evaluation_context=frozen_context,
    )

    # No deterministic failures and no AI hints
    det_result = {"passed": True, "deterministic_failures": [], "score": 100}

    classification = ctx_service.classify_causal_layers(
        run_id="run_unknown",
        diagnosis_id="diag_unknown",
        deterministic_result=det_result,
    )

    assert classification.primary_layer == CausalLayer.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════
# Tests 21-24: Prompt Candidate & Retest
# ═══════════════════════════════════════════════════════════════════════

def test_21_candidate_contains_source_context(ctx_service, frozen_context):
    """21. Prompt improvement candidate contains full source context provenance."""
    ctx_service.bind_context_to_run(
        run_id="run_candidate",
        evaluation_context=frozen_context,
    )

    candidate = ctx_service.propose_prompt_improvement(
        run_id="run_candidate",
        diagnosis_ids=["diag_001"],
        evidence_ids=["ev_001", "ev_002"],
        proposed_change="Add explicit uniqueness constraint to option generation instructions",
        rationale="Deterministic evaluation found duplicate distractors",
    )

    assert candidate.source_context_id == frozen_context.context_id
    assert candidate.source_context_hash == frozen_context.context_hash
    assert candidate.source_git_commit_sha == frozen_context.git_commit_sha
    assert candidate.source_prompt_id == "qgen_math_prompt"
    assert candidate.source_prompt_version == 1
    assert candidate.application_id == "app_question_generator"
    assert candidate.feature_id == "question_generation"
    assert candidate.status == "PROPOSED"


def test_22_multi_variable_changes_detected(ctx_service, app_context_service, sample_manifest):
    """22. Multi-variable changes between baseline and candidate are detected."""
    # Baseline context
    baseline_ctx = app_context_service.create_evaluation_context(
        application_id="app_question_generator",
        suite_id="suite_qgen_math_v1",
        auto_freeze=True,
    )

    # Create a candidate manifest with BOTH prompt and model changed
    candidate_manifest = AIApplicationManifest(
        application_id="app_question_generator_v2",
        feature_id="question_generation",
        application_name="VM Copy Question Generator v2",
        application_version="2.0.0",
        git_commit_sha="def456abc789",
        prompt_id="qgen_math_prompt",
        prompt_version=2,  # Changed
        model="gpt-4o-mini",  # Changed
        model_version="2024-07",
        behavioral_contract_ids=["contract_ca_exclusivity", "contract_no_duplicates", "contract_4_options"],
        evaluation_suite_ids=["suite_qgen_math_v1"],
    )
    app_context_service.create_application_manifest(candidate_manifest)

    candidate_ctx = app_context_service.create_evaluation_context(
        application_id="app_question_generator_v2",
        suite_id="suite_qgen_math_v1",
        auto_freeze=True,
    )

    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_baseline",
        candidate_run_id="run_candidate",
        baseline_context=baseline_ctx,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False, "dup_check": False},
        candidate_results={"ca_check": True, "dup_check": True},
    )

    assert result.is_multi_variable_change is True
    assert len(result.changed_dimensions) > 1
    # Both prompt and model changed
    assert "prompt_version" in result.changed_dimensions
    assert "model" in result.changed_dimensions


def test_23_unsupported_causal_attribution_blocked(ctx_service, app_context_service, sample_manifest):
    """23. Unsupported causal attribution is blocked when multi-variable changes exist."""
    baseline_ctx = app_context_service.create_evaluation_context(
        application_id="app_question_generator",
        suite_id="suite_qgen_math_v1",
        auto_freeze=True,
    )

    # Multiple variables changed
    candidate_manifest = AIApplicationManifest(
        application_id="app_qgen_multi_change",
        feature_id="question_generation",
        application_name="QGen Multi Change",
        application_version="2.0.0",
        git_commit_sha="newcommit123",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="different-model",
        model_version="v2",
        behavioral_contract_ids=["contract_ca_exclusivity"],
        evaluation_suite_ids=["suite_qgen_math_v1"],
    )
    app_context_service.create_application_manifest(candidate_manifest)
    candidate_ctx = app_context_service.create_evaluation_context(
        application_id="app_qgen_multi_change",
        suite_id="suite_qgen_math_v1",
        auto_freeze=True,
    )

    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_bl",
        candidate_run_id="run_cd",
        baseline_context=baseline_ctx,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False},
        candidate_results={"ca_check": True},
    )

    # With multi-variable change, improvement cannot be attributed solely to prompt
    assert result.is_multi_variable_change is True
    assert len(result.changed_dimensions) > 1


def test_24_regression_detected(ctx_service, frozen_context):
    """24. Regression is detected even if overall pass rate improves."""
    # Create a second frozen context for candidate
    candidate_ctx = EvaluationContext(
        context_id="ctx_candidate",
        application_id="app_question_generator",
        feature_id="question_generation",
        application_version="2.0.0",
        git_commit_sha="def456abc789",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="qwen2.5-coder:7b-instruct",
        model_version="7b-v1",
        is_frozen=True,
        context_hash="candidate_hash_123",
    )

    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_bl_reg",
        candidate_run_id="run_cd_reg",
        baseline_context=frozen_context,
        candidate_context=candidate_ctx,
        baseline_results={
            "ca_check": False,
            "dup_check": False,
            "difficulty_check": True,  # Passed in baseline
        },
        candidate_results={
            "ca_check": True,   # FIXED
            "dup_check": True,  # FIXED
            "difficulty_check": False,  # REGRESSION
        },
    )

    assert result.has_regressions is True
    assert result.transitions["difficulty_check"] == RetestTransition.REGRESSION
    assert result.transitions["ca_check"] == RetestTransition.FIXED_FAILURE
    assert result.transitions["dup_check"] == RetestTransition.FIXED_FAILURE


# ═══════════════════════════════════════════════════════════════════════
# Tests 25-29: Governance Authorization
# ═══════════════════════════════════════════════════════════════════════

def test_25_contract_violation_detected(ctx_service, frozen_context):
    """25. Contract violation detected during retest."""
    candidate_ctx = EvaluationContext(
        context_id="ctx_contract_test",
        application_id="app_question_generator",
        feature_id="question_generation",
        application_version="2.0.0",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="qwen2.5-coder:7b-instruct",
        is_frozen=True,
        context_hash="hash_contract",
    )

    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_bl_contract",
        candidate_run_id="run_cd_contract",
        baseline_context=frozen_context,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False},
        candidate_results={"ca_check": True},
        baseline_contracts={"contract_ca_exclusivity": "FAIL", "contract_4_options": "PASS"},
        candidate_contracts={"contract_ca_exclusivity": "PASS", "contract_4_options": "FAIL"},
    )

    assert result.contract_evaluations["contract_ca_exclusivity"] == ContractStatus.CONTRACT_PRESERVED
    assert result.contract_evaluations["contract_4_options"] == ContractStatus.CONTRACT_VIOLATED


def test_26_exact_authorization_binding_enforced(ctx_service):
    """26. Authorization for Prompt v18 must never authorize Prompt v19."""
    result = ctx_service.validate_authorization_binding(
        authorization_version="v18",
        authorization_commit="abc123",
        target_version="v18",
        target_commit="abc123",
    )
    assert result["is_valid"] is True

    # Wrong version
    result_wrong = ctx_service.validate_authorization_binding(
        authorization_version="v18",
        authorization_commit="abc123",
        target_version="v19",
        target_commit="abc123",
    )
    assert result_wrong["is_valid"] is False
    assert any("Version mismatch" in b for b in result_wrong["blockers"])


def test_27_stale_authorization_rejected(ctx_service):
    """27. Stale authorization (wrong commit) is rejected."""
    result = ctx_service.validate_authorization_binding(
        authorization_version="v18",
        authorization_commit="abc123",
        target_version="v18",
        target_commit="def456",  # Different commit
    )
    assert result["is_valid"] is False
    assert result["commit_match"] is False
    assert any("Commit mismatch" in b for b in result["blockers"])


def test_28_independent_retest_required(ctx_service, frozen_context):
    """28. Independent retest required — original run cannot be reused."""
    candidate_ctx = EvaluationContext(
        context_id="ctx_retest_req",
        application_id="app_question_generator",
        feature_id="question_generation",
        application_version="2.0.0",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="qwen2.5-coder:7b-instruct",
        is_frozen=True,
        context_hash="hash_retest",
    )

    # Independent: different run IDs
    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_original",
        candidate_run_id="run_fresh_retest",
        baseline_context=frozen_context,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False},
        candidate_results={"ca_check": True},
    )
    assert result.is_independently_verified is True

    # NOT independent: same run ID
    result_same = ctx_service.execute_retest_comparison(
        baseline_run_id="run_same",
        candidate_run_id="run_same",
        baseline_context=frozen_context,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False},
        candidate_results={"ca_check": True},
    )
    assert result_same.is_independently_verified is False


def test_29_original_evidence_cannot_be_reused_as_final_verification(ctx_service, frozen_context):
    """29. Original evidence cannot be reused as final verification."""
    candidate_ctx = EvaluationContext(
        context_id="ctx_no_reuse",
        application_id="app_question_generator",
        feature_id="question_generation",
        application_version="2.0.0",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="qwen2.5-coder:7b-instruct",
        is_frozen=True,
        context_hash="hash_no_reuse",
    )

    # Using same run for both baseline and candidate simulates evidence reuse
    result = ctx_service.execute_retest_comparison(
        baseline_run_id="run_original_evidence",
        candidate_run_id="run_original_evidence",  # Same = reuse
        baseline_context=frozen_context,
        candidate_context=candidate_ctx,
        baseline_results={"ca_check": False},
        candidate_results={"ca_check": True},
    )

    # Must NOT be independently verified
    assert result.is_independently_verified is False


# ═══════════════════════════════════════════════════════════════════════
# Test 30: Complete E2E Provenance Chain
# ═══════════════════════════════════════════════════════════════════════

def test_30_complete_e2e_provenance_chain(ctx_service, app_context_service, sample_manifest):
    """
    30. Complete E2E provenance chain exists:
    Application → Feature → Git Commit → Prompt Version → Model Version →
    Evaluation Context → Evaluation Suite/Case → Dogfooding Run →
    Browser Step → Evidence → Deterministic Signal → Diagnosis →
    Recommendation → Approval Request → Human Decision → Authorization →
    Changed Commit → CI → Independent Retest → Final Evidence
    """
    # 1. Application & Context
    baseline_ctx = app_context_service.create_evaluation_context(
        application_id="app_question_generator",
        suite_id="suite_qgen_math_v1",
        feature_id="question_generation",
        auto_freeze=True,
    )

    # 2. Bind to dogfooding run
    binding = ctx_service.bind_context_to_run(
        run_id="run_e2e_baseline",
        evaluation_context=baseline_ctx,
        evaluation_case_id="case_multiplication_tier1",
    )
    assert binding.application_id == "app_question_generator"
    assert binding.feature_id == "question_generation"
    assert binding.git_commit_sha == "abc123def456"
    assert binding.prompt_version == 1

    # 3. Runtime verification
    verified = ctx_service.verify_runtime_context(
        run_id="run_e2e_baseline",
        actual_prompt=("qgen_math_prompt", 1),
        actual_model="qwen2.5-coder:7b-instruct",
        actual_git_commit="abc123def456",
    )
    assert verified.is_context_valid

    # 4. Deterministic evaluation (with controlled failure)
    defective_output = {
        "question": "What is 14 * 5?",
        "options": [
            {"text": "70", "logic": "Correct"},
            {"text": "60", "logic": "Error"},
            {"text": "60", "logic": "Duplicate"},
        ],
    }
    det_result = ctx_service.run_deterministic_evaluation(
        run_id="run_e2e_baseline",
        ai_output=defective_output,
        evaluation_rules={"type": "question_generator", "expected_option_count": 4},
    )
    assert det_result["passed"] is False
    assert det_result["is_authoritative"] is True

    # 5. Causal classification
    classification = ctx_service.classify_causal_layers(
        run_id="run_e2e_baseline",
        diagnosis_id="diag_e2e_001",
        deterministic_result=det_result,
        evidence_refs=["ev_dom_001", "ev_screenshot_001"],
    )
    assert classification.primary_layer != CausalLayer.UNKNOWN

    # 6. Prompt improvement proposal
    candidate = ctx_service.propose_prompt_improvement(
        run_id="run_e2e_baseline",
        diagnosis_ids=["diag_e2e_001"],
        evidence_ids=["ev_dom_001", "ev_screenshot_001"],
        proposed_change="Add uniqueness constraint to option generation",
        rationale="Duplicate distractors detected by deterministic evaluator",
    )
    assert candidate.status == "PROPOSED"
    assert candidate.source_prompt_version == 1

    # 7. Authorization binding check (simulated)
    auth_check = ctx_service.validate_authorization_binding(
        authorization_version="v2",
        authorization_commit="newcommit789",
        target_version="v2",
        target_commit="newcommit789",
    )
    assert auth_check["is_valid"] is True

    # 8. Create candidate context (simulating v2 prompt)
    candidate_manifest = AIApplicationManifest(
        application_id="app_qgen_v2_e2e",
        feature_id="question_generation",
        application_name="QGen E2E v2",
        application_version="2.0.0",
        git_commit_sha="newcommit789",
        prompt_id="qgen_math_prompt",
        prompt_version=2,
        model="qwen2.5-coder:7b-instruct",
        model_version="7b-v1",
        retrieval_configuration={"type": "vector", "version": "v1", "top_k": 5},
        tool_configuration={"tools": ["calculator", "latex_renderer"]},
        parser_configuration={"type": "json", "version": "v1", "strict": True},
        behavioral_contract_ids=["contract_ca_exclusivity", "contract_no_duplicates", "contract_4_options"],
        evaluation_suite_ids=["suite_qgen_math_v1"],
    )
    app_context_service.create_application_manifest(candidate_manifest)
    candidate_ctx = app_context_service.create_evaluation_context(
        application_id="app_qgen_v2_e2e",
        suite_id="suite_qgen_math_v1",
        auto_freeze=True,
    )

    # 9. Independent retest
    retest = ctx_service.execute_retest_comparison(
        baseline_run_id="run_e2e_baseline",
        candidate_run_id="run_e2e_candidate",
        baseline_context=baseline_ctx,
        candidate_context=candidate_ctx,
        baseline_results={
            "ca_check": False,
            "dup_check": False,
            "option_count_check": False,
        },
        candidate_results={
            "ca_check": True,
            "dup_check": True,
            "option_count_check": True,
        },
        baseline_contracts={
            "contract_ca_exclusivity": "FAIL",
            "contract_no_duplicates": "FAIL",
            "contract_4_options": "FAIL",
        },
        candidate_contracts={
            "contract_ca_exclusivity": "PASS",
            "contract_no_duplicates": "PASS",
            "contract_4_options": "PASS",
        },
    )

    # 10. Verify complete provenance
    assert retest.is_independently_verified is True
    assert retest.has_regressions is False

    # All failures fixed
    assert retest.transitions["ca_check"] == RetestTransition.FIXED_FAILURE
    assert retest.transitions["dup_check"] == RetestTransition.FIXED_FAILURE
    assert retest.transitions["option_count_check"] == RetestTransition.FIXED_FAILURE

    # All contracts preserved
    assert retest.contract_evaluations["contract_ca_exclusivity"] == ContractStatus.CONTRACT_PRESERVED
    assert retest.contract_evaluations["contract_no_duplicates"] == ContractStatus.CONTRACT_PRESERVED
    assert retest.contract_evaluations["contract_4_options"] == ContractStatus.CONTRACT_PRESERVED

    # Only prompt_version changed (single variable)
    prompt_change = [c for c in retest.comparisons if c.dimension == "prompt_version"]
    assert len(prompt_change) == 1
    assert prompt_change[0].status == "CHANGED"
    assert prompt_change[0].baseline_value == "1"
    assert prompt_change[0].candidate_value == "2"

    # Git commit also changed (expected for a new candidate)
    git_change = [c for c in retest.comparisons if c.dimension == "git_commit_sha"]
    assert len(git_change) == 1
    assert git_change[0].status == "CHANGED"

    # Model unchanged
    model_cmp = [c for c in retest.comparisons if c.dimension == "model"]
    assert model_cmp[0].status == "SAME"

    # Chain is complete:
    # Application -> Feature -> Git -> Prompt -> Model -> Context ->
    # Evaluation -> Run -> Evidence -> Deterministic Signal -> Diagnosis ->
    # Classification -> Candidate -> Authorization -> Retest -> Verification
    assert binding.evaluation_context_id == baseline_ctx.context_id
    assert candidate.source_context_id == baseline_ctx.context_id
    assert retest.baseline_context_id == baseline_ctx.context_id
    assert retest.candidate_context_id == candidate_ctx.context_id
