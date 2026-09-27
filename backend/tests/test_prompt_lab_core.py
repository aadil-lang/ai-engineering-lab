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
    GroundingStatus,
    SeverityLevel,
    FailureCause,
    EpistemicType,
    CandidateStatus,
    CaseTransition,
    AIExecutionRecord,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.prompt_service import PromptService
from backend.app.prompt_lab.evaluator_service import (
    JSONSchemaEvaluator,
    RuleBasedEvaluator,
    ExactMatchEvaluator,
    CodeExecutionEvaluator,
    SQLExecutionEvaluator,
    GroundingEvaluator,
    SemanticJudgeEvaluator,
    CompositeEvaluator,
)
from backend.app.prompt_lab.diagnosis_service import PromptDiagnosisService
from backend.app.prompt_lab.evaluation_service import EvaluationService
from backend.app.prompt_lab.errors import (
    PromptVersionImmutableError,
    InvalidPromptTemplateError,
    EvaluationSnapshotTamperedError,
    PromptNotFoundError,
)


@pytest.fixture
def repo():
    return PromptLabRepository(db_path=":memory:")


@pytest.fixture
def prompt_service(repo):
    return PromptService(repo)


@pytest.fixture
def diagnosis_service():
    return PromptDiagnosisService()


@pytest.fixture
def eval_service(repo, prompt_service, diagnosis_service):
    return EvaluationService(repo, prompt_service, diagnosis_service)


# 1. Prompt Version Immutability
def test_prompt_version_immutability(repo, prompt_service):
    prompt_service.create_prompt("prompt_triage", "Ticket Triage", "Categorizes incoming tickets")
    pv1 = prompt_service.create_prompt_version(
        prompt_id="prompt_triage",
        template="Classify ticket: {{ticket}}",
        variables_schema={"required": ["ticket"]},
    )
    assert pv1.version == 1
    assert not pv1.is_evaluated

    # Mark as evaluated
    repo.mark_prompt_version_evaluated("prompt_triage", 1)
    pv1_reloaded = prompt_service.get_prompt_version("prompt_triage", 1)
    assert pv1_reloaded.is_evaluated

    # Attempting to mutate evaluated version must raise error
    with pytest.raises(PromptVersionImmutableError):
        mutated = PromptVersion(
            prompt_id="prompt_triage",
            version=1,
            template="MUTATED: Classify ticket: {{ticket}}",
        )
        repo.save_prompt_version(mutated)


# 2. Prompt Rendering & Variable Validation
def test_prompt_rendering_and_variable_validation(prompt_service):
    prompt_service.create_prompt("prompt_greet", "Greeter")
    pv = prompt_service.create_prompt_version(
        prompt_id="prompt_greet",
        template="Hello {{name}}, welcome to {{service}}!",
        variables_schema={"required": ["name", "service"]},
    )

    rendered, h = prompt_service.render_prompt(pv, {"name": "Alice", "service": "Antigravity"})
    assert rendered == "Hello Alice, welcome to Antigravity!"
    assert len(h) == 64

    # Missing required variable raises error
    with pytest.raises(InvalidPromptTemplateError):
        prompt_service.render_prompt(pv, {"name": "Alice"})


# 3. Secret Redaction
def test_secret_redaction_in_prompt_and_outputs(prompt_service):
    prompt_service.create_prompt("prompt_sec", "Security Prompt")
    pv = prompt_service.create_prompt_version(
        prompt_id="prompt_sec",
        template="Token is {{token}}",
    )
    rendered, _ = prompt_service.render_prompt(pv, {"token": "ghp_1234567890abcdef1234567890abcdef"})
    assert "ghp_1234567890abcdef1234567890abcdef" not in rendered
    assert "[REDACTED_SECRET]" in rendered


# 4. JSON Schema Evaluator
def test_json_schema_evaluator():
    evaluator = JSONSchemaEvaluator()
    schema = {
        "type": "object",
        "required": ["category", "priority"],
        "properties": {
            "category": {"type": "string"},
            "priority": {"type": "integer"},
        },
    }

    # Pass
    res_pass = evaluator.evaluate('{"category": "billing", "priority": 1}', schema)
    assert res_pass.status == EvaluationStatus.PASS
    assert res_pass.score == 1.0

    # Missing required field
    res_missing = evaluator.evaluate('{"category": "billing"}', schema)
    assert res_missing.status == EvaluationStatus.FAIL
    assert "Missing required" in res_missing.rationale

    # Type mismatch
    res_type = evaluator.evaluate('{"category": "billing", "priority": "high"}', schema)
    assert res_type.status == EvaluationStatus.FAIL
    assert "type violations" in res_type.rationale

    # Invalid JSON
    res_invalid = evaluator.evaluate("Not a json at all", schema)
    assert res_invalid.status == EvaluationStatus.FAIL
    assert "not valid JSON" in res_invalid.rationale


# 5. Rule-Based Evaluator
def test_rule_based_evaluator():
    evaluator = RuleBasedEvaluator()
    constraints = [
        "forbidden: as an ai language model, confidential",
        "required_phrase: Recommended Action:",
        "max_chars: 200",
    ]

    # Clean pass
    good_output = "Ticket analysis complete. Recommended Action: Escalate to Level 2."
    res_good = evaluator.evaluate(good_output, constraints)
    assert res_good.status == EvaluationStatus.PASS

    # Forbidden phrase violation
    bad_output = "As an AI language model, here is the ticket. Recommended Action: None."
    res_bad = evaluator.evaluate(bad_output, constraints)
    assert res_bad.status == EvaluationStatus.FAIL
    assert "Forbidden phrase" in res_bad.rationale

    # Missing required phrase
    missing_output = "Ticket analysis done. Everything is fine."
    res_missing = evaluator.evaluate(missing_output, constraints)
    assert res_missing.status == EvaluationStatus.FAIL
    assert "Required phrase missing" in res_missing.rationale


# 6. Exact Match Evaluator
def test_exact_match_evaluator():
    evaluator = ExactMatchEvaluator()
    assert evaluator.evaluate("YES", "YES").status == EvaluationStatus.PASS
    assert evaluator.evaluate("NO", "YES").status == EvaluationStatus.FAIL
    assert evaluator.evaluate("text", None).status == EvaluationStatus.NOT_APPLICABLE


# 7. Code & SQL Execution Evaluator
def test_code_execution_evaluator_safety():
    evaluator = CodeExecutionEvaluator()

    # Valid safe code
    safe_code = "result = sum([1, 2, 3, 4])"
    res_safe = evaluator.evaluate(safe_code, "computes sum")
    assert res_safe.status == EvaluationStatus.PASS

    # Disallowed dangerous import
    evil_code = "import os\nos.system('dir')"
    res_evil = evaluator.evaluate(evil_code, "danger")
    assert res_evil.status == EvaluationStatus.FAIL
    assert "Security violation" in res_evil.rationale

    # Disallowed call
    eval_call = "x = eval('2 + 2')"
    res_eval = evaluator.evaluate(eval_call, "danger")
    assert res_eval.status == EvaluationStatus.FAIL


def test_sql_execution_evaluator_safety():
    evaluator = SQLExecutionEvaluator()

    # Valid select
    res_select = evaluator.evaluate("SELECT 1 AS num", schema_ddl=None)
    assert res_select.status == EvaluationStatus.PASS

    # Forbidden DDL/mutation
    res_drop = evaluator.evaluate("DROP TABLE users;")
    assert res_drop.status == EvaluationStatus.FAIL
    assert "Security violation" in res_drop.rationale


# 8. Grounding Evaluator
def test_grounding_evaluator():
    evaluator = GroundingEvaluator()
    sources = [
        {"source_id": "src1", "content": "Antigravity Engineering Lab provides independent runtime verification for AI applications."}
    ]

    # Grounded claim
    grounded_output = "The Antigravity Engineering Lab provides independent runtime verification."
    res_grounded = evaluator.evaluate(grounded_output, sources)
    assert res_grounded.status == EvaluationStatus.PASS
    assert res_grounded.score >= 0.8

    # Hallucinated / ungrounded claim
    hallucinated_output = "The application uses quantum computing teleportation protocols to accelerate database queries."
    res_hallucinated = evaluator.evaluate(hallucinated_output, sources)
    assert res_hallucinated.status == EvaluationStatus.FAIL
    assert res_hallucinated.score == 0.0

    # Empty sources returns UNKNOWN
    res_empty = evaluator.evaluate("Some statement", sources=[])
    assert res_empty.status == EvaluationStatus.UNKNOWN


# 9. Semantic Judge Evaluator
def test_semantic_judge_evaluator():
    evaluator = SemanticJudgeEvaluator()

    # High alignment
    res = evaluator.evaluate(
        raw_output="The diagnosed defect was caused by a stale cache entry causing state divergence.",
        expected_behavior="Explain that stale cache caused state divergence.",
    )
    assert res.status == EvaluationStatus.PASS
    assert res.score >= 0.7

    # Execution failure
    res_err = evaluator.evaluate(
        raw_output="Internal error: Unhandled exception occurred while formatting response.",
        expected_behavior="Return triage categorization.",
    )
    assert res_err.status == EvaluationStatus.FAIL


# 10. Composite Evaluator & Non-Override Invariant
def test_composite_evaluator_deterministic_precedence():
    comp = CompositeEvaluator()
    case = EvaluationCase(
        case_id="case_1",
        input={"text": "hello"},
        expected_behavior="Return structured greeting in JSON",
        constraints=["forbidden: badword"],
        evaluation_strategy=EvaluationStrategy.COMPOSITE,
    )

    # Output has great semantic text, but violates rule constraint
    output_violating_rule = "Hello there! This is a badword."
    status, results, score = comp.evaluate_case(case, output_violating_rule, output_schema=None)
    assert status == EvaluationStatus.FAIL
    assert any(r.strategy == EvaluationStrategy.RULE_BASED and r.status == EvaluationStatus.FAIL for r in results)


# 11. Epistemic UNKNOWN and ABSTAINED Preservation
def test_composite_evaluator_preserves_unknown_and_abstained():
    comp = CompositeEvaluator()
    # Case with grounding evaluation where sources are empty -> Grounding produces UNKNOWN
    case = EvaluationCase(
        case_id="case_unknown",
        input={"query": "test"},
        expected_behavior="Grounded answer",
        sources=[],
        evaluation_strategy=EvaluationStrategy.GROUNDING,
    )
    status, results, score = comp.evaluate_case(case, "Some arbitrary claim that requires verification", output_schema=None)
    assert status == EvaluationStatus.UNKNOWN


# 12. Diagnosis Grounding (OBSERVED, INFERRED, HYPOTHESIS)
def test_diagnosis_grounding_epistemic_separation(diagnosis_service):
    case = EvaluationCase(
        case_id="case_err",
        input={"ticket": "broken checkout"},
        expected_behavior="Output JSON with priority",
    )
    evaluator_results = [
        JSONSchemaEvaluator().evaluate('{"status": "open"}', {"required": ["priority"]})
    ]
    diag = diagnosis_service.diagnose_failure("run_001", case, evaluator_results)
    assert diag.primary_cause in {FailureCause.PROMPT_DEFECT, FailureCause.SCHEMA_FAILURE}

    types = {f.epistemic_type for f in diag.facts}
    assert EpistemicType.OBSERVED in types
    assert EpistemicType.INFERRED in types
    assert EpistemicType.HYPOTHESIS in types
    assert "missing required" in diag.observed_summary.lower()


# 13. Snapshot Immutability & Tampering Protection
def test_snapshot_immutability_and_tampering(eval_service, repo):
    eval_service.prompt_service.create_prompt("prompt_snap", "Snap Prompt")
    pv = eval_service.prompt_service.create_prompt_version("prompt_snap", "Hello {{name}}")
    eval_service.create_suite("suite_snap", "Snap Suite")
    sv = eval_service.create_suite_version(
        "suite_snap",
        cases=[
            EvaluationCase(
                case_id="c1",
                input={"name": "World"},
                expected_behavior="Say hello",
                expected_output="Response addressing: Say hello.",
            )
        ]
    )

    run = eval_service.execute_evaluation("prompt_snap", pv.version, "suite_snap", sv.version)
    snap_id = f"eval_snap_{run.prompt_id}_v{run.prompt_version}_{run.suite_id}_v{run.suite_version}"
    snap = repo.get_snapshot(snap_id)
    assert snap is not None
    assert len(snap.sha256_hash) == 64

    # Tampering with snapshot hash raises error
    snap.sha256_hash = "tampered_hash_00000000000000000000000000000000000000000000000000"
    with pytest.raises(EvaluationSnapshotTamperedError):
        repo.save_snapshot(snap)
