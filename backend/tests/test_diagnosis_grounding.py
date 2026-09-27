import pytest
import uuid
from backend.app.models.enums import (
    ClaimType,
    GroundingStatus,
    FailureCategory,
    Severity,
    TestMode,
    RunStatus,
    ActionType,
    ActionStatus,
)
from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_action import TestAction
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.diagnosis import (
    EngineeringDiagnosis,
    EvidenceBundle,
    DeterministicSignal,
    DiagnosisClaim,
)
from backend.app.diagnosis.deterministic_analyzer import DeterministicAnalyzer
from backend.app.diagnosis.grounding_validator import DiagnosisGroundingValidator
from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.remediation.coding_agent import MockCodingAgent, OllamaCodingAgent

@pytest.fixture
def temp_db(tmp_path):
    from backend.app.core.database import init_db
    db_file = str(tmp_path / "test_grounding.db")
    init_db(db_file)
    return SQLiteRepository(db_file)

def test_grounding_supported_claim():
    """Verify that claims supported by deterministic assertion signals receive SUPPORTED status."""
    validator = DiagnosisGroundingValidator()

    bundle = EvidenceBundle(
        run_id="run_101",
        target_id="eda_platform",
        target_url="http://localhost:8000",
        test_mode="FUNCTIONAL_QA",
        error_message="AssertionError: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS in test_analysis_planner.py",
        deterministic_signals=[
            DeterministicSignal(
                signal_type="ASSERTION_ERROR",
                summary="Assertion condition failed: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS",
                details={"error": "AssertionError: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS"},
            )
        ],
    )

    raw_diag = EngineeringDiagnosis(
        run_id="run_101",
        title="AssertionError: AnalysisStatus mismatch",
        root_cause_summary="The test expected AnalysisStatus.READY but observed AnalysisStatus.MISSING_INPUTS during planner evaluation.",
        failure_category=FailureCategory.ASSERTION_FAILURE,
        confidence_score=0.95,
        suspected_component="AnalysisPlanner",
        suggested_fix="Ensure all required design inputs are populated before evaluating AnalysisStatus.",
        regression_test_spec="def test_regression(): assert planner.status == READY",
    )

    validated = validator.validate(raw_diag, bundle)

    assert validated.is_grounded is True
    assert validated.grounding_score >= 0.8
    assert len(validated.claims) >= 3
    
    # Root cause claim should be SUPPORTED with evidence references
    rc_claim = next(c for c in validated.claims if c.claim_type == ClaimType.ROOT_CAUSE)
    assert rc_claim.grounding_status == GroundingStatus.SUPPORTED
    assert len(rc_claim.evidence_refs) > 0
    assert any("signal:ASSERTION_ERROR" in ref for ref in rc_claim.evidence_refs)

def test_grounding_detects_contradicted_claim_and_synthesizes_correction():
    """
    Controlled Failure Experiment Scenario:
    Qwen diagnosed the Python unit test failure as a 'Frontend / Backend API network mismatch'.
    Validator must identify the contradiction, flag CONTRADICTED, and ground the root cause to deterministic truth.
    """
    validator = DiagnosisGroundingValidator()

    # Evidence from real Python unit test failure with zero network calls
    bundle = EvidenceBundle(
        run_id="run_exp_controlled",
        target_id="eda_platform",
        target_url="http://localhost:8000",
        test_mode="FUNCTIONAL_QA",
        error_message="AssertionError: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS in backend/tests/test_analysis_planner.py",
        deterministic_signals=[
            DeterministicSignal(
                signal_type="ASSERTION_ERROR",
                summary="Assertion condition failed: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS",
                details={"error": "AssertionError: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS"},
            )
        ],
        failed_network_calls=[],
        console_errors=[],
    )

    # Hallucinated raw diagnosis blaming frontend/API network mismatch
    raw_diag = EngineeringDiagnosis(
        run_id="run_exp_controlled",
        title="Frontend / Backend API Contract Mismatch",
        root_cause_summary="The frontend received MISSING_INPUTS from the backend API gateway due to an HTTP network payload discrepancy.",
        failure_category=FailureCategory.FUNCTIONAL_BUG,
        confidence_score=0.90,
        suspected_component="Frontend Navigation Component & Backend API Gateway",
        suggested_fix="Update frontend API client to parse response correctly.",
        regression_test_spec="test('frontend api check', async () => {});",
    )

    validated = validator.validate(raw_diag, bundle)

    # Must flag contradiction and not be grounded
    assert validated.is_grounded is False
    assert validated.grounding_score < 0.7

    rc_claim = next(c for c in validated.claims if c.claim_type == ClaimType.ROOT_CAUSE)
    assert rc_claim.grounding_status == GroundingStatus.CONTRADICTED

    comp_claim = next(c for c in validated.claims if c.claim_type == ClaimType.COMPONENT)
    assert comp_claim.grounding_status == GroundingStatus.CONTRADICTED

    # Grounded fields must be automatically corrected to deterministic reality
    assert validated.grounded_root_cause is not None
    assert "Deterministic Assertion Failure" in validated.grounded_root_cause
    assert "AnalysisStatus.READY" in validated.grounded_root_cause or "Assertion condition failed" in validated.grounded_root_cause
    assert "Backend Module" in validated.grounded_suspected_component or "eda_platform" in validated.grounded_suspected_component
    assert len(validated.validation_notes) > 0

def test_grounding_detects_unsupported_claim():
    """Verify that claims with zero supporting evidence are marked UNSUPPORTED without fabricated refs."""
    validator = DiagnosisGroundingValidator()

    bundle = EvidenceBundle(
        run_id="run_102",
        target_id="eda_platform",
        target_url="http://localhost:8000",
        test_mode="FUNCTIONAL_QA",
        error_message="Simple timeout error",
        deterministic_signals=[
            DeterministicSignal(
                signal_type="TIMEOUT",
                summary="Execution step timed out waiting for action",
                details={},
            )
        ],
    )

    raw_diag = EngineeringDiagnosis(
        run_id="run_102",
        title="Database Deadlock Failure",
        root_cause_summary="PostgreSQL connection pool exhausted due to unindexed foreign key lock.",
        failure_category=FailureCategory.FUNCTIONAL_BUG,
        confidence_score=0.85,
        suspected_component="Database Cluster",
        suggested_fix="Add index to foreign keys.",
        regression_test_spec="// test",
    )

    validated = validator.validate(raw_diag, bundle)

    rc_claim = next(c for c in validated.claims if c.claim_type == ClaimType.ROOT_CAUSE)
    assert rc_claim.grounding_status == GroundingStatus.UNSUPPORTED
    assert rc_claim.evidence_refs == []

def test_full_diagnosis_service_grounding_persistence(temp_db):
    """End-to-end test verifying DiagnosisService, independent validator, and SQLite persistence."""
    repo = temp_db

    # Create Target & Run
    target = ApplicationTarget(
        target_id="tgt_eda",
        name="Engineering Design Automation",
        target_type="WEB_APPLICATION",
        base_url="http://localhost:8000",
        environment="TEST",
        version="1.0.0",
    )
    repo.create_target(target)

    run = TestRun(
        run_id="run_db_grounding_test",
        application_id="tgt_eda",
        application_version="1.0.0",
        test_mode=TestMode.FUNCTIONAL_QA,
        status=RunStatus.FAILED,
        environment_id="env_local",
        actions=[
            TestAction(
                action_type=ActionType.ASSERT,
                description="Verify analysis status is READY",
                status=ActionStatus.FAILED,
                error_message="AssertionError: expected READY, observed MISSING_INPUTS",
            )
        ],
    )
    repo.create_run(run)

    failure = Failure(
        failure_id="fail_db_test",
        run_id="run_db_grounding_test",
        category=FailureCategory.ASSERTION_FAILURE,
        severity=Severity.HIGH,
        title="Assertion Failed",
        message="expected READY, observed MISSING_INPUTS",
    )
    repo.save_failure(failure)

    # Initialize Service
    service = DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=QwenDiagnostician(base_url="http://localhost:99999"),
        validator=DiagnosisGroundingValidator(),
    )

    diag = service.diagnose_run("run_db_grounding_test")

    assert diag is not None
    assert diag.run_id == "run_db_grounding_test"
    assert len(diag.claims) > 0
    assert diag.is_grounded is True
    assert diag.grounding_score >= 0.6

    # Retrieve from DB and verify persistence
    loaded = repo.get_diagnosis_by_run("run_db_grounding_test")
    assert loaded is not None
    assert loaded.diagnosis_id == diag.diagnosis_id
    assert len(loaded.claims) == len(diag.claims)
    assert loaded.grounding_score == diag.grounding_score
    assert loaded.is_grounded == diag.is_grounded

def test_coding_agent_consumes_grounded_diagnosis():
    """Verify that MockCodingAgent and OllamaCodingAgent prioritize grounded fields over contradicted raw hypotheses."""
    import asyncio
    
    async def _run():
        agent = MockCodingAgent()

        # Diagnosis where raw hypothesis is contradicted, but grounded fields are corrected
        diagnosis = EngineeringDiagnosis(
            run_id="run_remed_test",
            title="Test Failure",
            root_cause_summary="Hallucinated API Gateway Discrepancy",
            grounded_root_cause="Deterministic Assertion Failure: expected AnalysisStatus.READY, observed AnalysisStatus.MISSING_INPUTS",
            failure_category=FailureCategory.ASSERTION_FAILURE,
            confidence_score=0.9,
            suspected_component="Frontend UI Gateway",
            grounded_suspected_component="backend/app/analysis/analysis_planner.py",
            suggested_fix="Populate default analysis inputs when initializing planner.",
            regression_test_spec="pytest backend/tests",
            is_grounded=False,
            grounding_score=0.4,
        )

        change = await agent.propose_change(
            repository="eda_platform",
            diagnosis=diagnosis,
            task_id="task_remed_1",
        )

        assert change is not None
        # Ensure coding agent targeted the grounded component rather than hallucinated component
        assert change.files[0].path == "backend/app/analysis/analysis_planner.py"
        assert "Deterministic Assertion Failure" in change.rationale

        # Test prompt building for OllamaCodingAgent
        ollama_agent = OllamaCodingAgent()
        prompt = ollama_agent._build_prompt(
            repository="eda_platform",
            diagnosis=diagnosis,
            evidence_bundle=None,
            reproduction_steps=None,
            relevant_files=None,
        )

        assert "VERIFIED TARGET COMPONENT: backend/app/analysis/analysis_planner.py" in prompt
        assert "EVIDENCE-GROUNDED ROOT CAUSE: Deterministic Assertion Failure" in prompt

    asyncio.run(_run())
