import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from backend.app.models.enums import RunStatus, ActionStatus, ActionType, EvidenceType, FailureCategory, Severity, TestMode
from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_action import TestAction
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.diagnosis import EngineeringDiagnosis, EvidenceBundle, DeterministicSignal
from backend.app.diagnosis.deterministic_analyzer import DeterministicAnalyzer
from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.repositories.sqlite_repository import SQLiteRepository

@pytest.fixture
def diagnosis_test_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_diag.db")
    repo = SQLiteRepository(db_path=db_path)

    target = ApplicationTarget(
        target_id="tgt_shop_app",
        name="Shop App",
        base_url="http://localhost:3000",
    )
    repo.create_target(target)

    # Create a failing run
    action1 = TestAction(
        action_type=ActionType.NAVIGATE,
        description="Navigate to /checkout",
        status=ActionStatus.PASSED,
        input_data={"url": "http://localhost:3000/checkout"},
        duration_ms=150,
    )
    action2 = TestAction(
        action_type=ActionType.CLICK,
        description="Click pay button",
        selector="#btn-pay",
        status=ActionStatus.FAILED,
        error_message="HTTP 500 Internal Server Error: Failed to charge card",
        input_data={"selector": "#btn-pay"},
        duration_ms=210,
    )

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        status=RunStatus.FAILED,
        natural_language_goal="Test user checkout flow",
        actions=[action1, action2],
    )
    repo.create_run(run)

    # Add console evidence with uncaught error
    console_evi = Evidence(
        run_id=run.run_id,
        evidence_type=EvidenceType.CONSOLE_LOG,
        title="Browser Console Log",
        payload={
            "events": [
                {"type": "error", "text": "Uncaught TypeError: Cannot read properties of undefined (reading 'token')"}
            ]
        },
    )
    repo.save_evidence(console_evi)

    # Add network HAR evidence with HTTP 500
    network_evi = Evidence(
        run_id=run.run_id,
        evidence_type=EvidenceType.NETWORK_HAR,
        title="Network Telemetry",
        payload={
            "events_sample": [
                {"event": "response", "url": "http://localhost:3000/api/charge", "status": 500, "status_text": "Internal Server Error", "ok": False}
            ]
        },
    )
    repo.save_evidence(network_evi)

    # Add failure record
    failure = Failure(
        run_id=run.run_id,
        action_id=action2.action_id,
        category=FailureCategory.FUNCTIONAL_BUG,
        severity=Severity.HIGH,
        title="Payment processing error",
        message="HTTP 500 Internal Server Error returned by /api/charge",
    )
    repo.save_failure(failure)
    run.failure_ids.append(failure.failure_id)
    repo.update_run(run)

    yield repo, target, run, [console_evi, network_evi], [failure]

def test_deterministic_analyzer_extracts_signals(diagnosis_test_env):
    repo, target, run, evidence_items, failures = diagnosis_test_env

    bundle = DeterministicAnalyzer.analyze(
        run=run,
        target=target,
        evidence_items=evidence_items,
        failures=failures,
    )

    assert bundle.run_id == run.run_id
    assert bundle.target_id == target.target_id
    assert bundle.failed_action_index == 2
    assert bundle.failed_action_type == "CLICK"
    assert bundle.failed_action_selector == "#btn-pay"

    # Verify signals
    signal_types = [s.signal_type for s in bundle.deterministic_signals]
    assert "CONSOLE_ERROR" in signal_types
    assert "HTTP_ERROR" in signal_types
    assert "ACTION_FAILED" in signal_types
    assert "FAILURE_RECORD" in signal_types

    assert len(bundle.console_errors) == 1
    assert "Cannot read properties of undefined" in bundle.console_errors[0]
    assert len(bundle.failed_network_calls) == 1
    assert bundle.failed_network_calls[0]["status"] == 500

def test_qwen_diagnostician_fallback_synthesis(diagnosis_test_env):
    repo, target, run, evidence_items, failures = diagnosis_test_env

    bundle = DeterministicAnalyzer.analyze(
        run=run,
        target=target,
        evidence_items=evidence_items,
        failures=failures,
    )

    # Use diagnostician in offline/fallback mode
    diagnostician = QwenDiagnostician()
    diagnosis = diagnostician._synthesize_deterministic_fallback(bundle, failure_id=failures[0].failure_id)

    assert diagnosis.run_id == run.run_id
    assert diagnosis.failure_id == failures[0].failure_id
    assert "500" in diagnosis.title or "Server" in diagnosis.title
    assert "Backend API" in diagnosis.suspected_component
    assert len(diagnosis.deterministic_signals) >= 3
    assert len(diagnosis.reproduction_steps) >= 2
    assert diagnosis.suggested_fix is not None
    assert diagnosis.regression_test_spec is not None
    assert "playwright" in diagnosis.regression_test_spec.lower()

def test_diagnosis_service_flow(diagnosis_test_env):
    repo, target, run, evidence_items, failures = diagnosis_test_env

    diagnostician = QwenDiagnostician()
    service = DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=diagnostician,
    )

    # 1. Diagnose Run
    diag = service.diagnose_run(run.run_id)
    assert diag.run_id == run.run_id
    assert diag.diagnosis_id.startswith("diag_")

    # 2. Get Run Diagnosis
    fetched = service.get_run_diagnosis(run.run_id)
    assert fetched is not None
    assert fetched.diagnosis_id == diag.diagnosis_id
    assert fetched.root_cause_summary == diag.root_cause_summary

    # 3. List Diagnoses
    all_diags = service.list_diagnoses()
    assert len(all_diags) == 1
    assert all_diags[0].diagnosis_id == diag.diagnosis_id

def test_api_diagnosis_endpoints(diagnosis_test_env):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.api.deps import get_diagnosis_service

    repo, target, run, evidence_items, failures = diagnosis_test_env
    app.dependency_overrides[get_diagnosis_service] = lambda: DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=QwenDiagnostician(),
    )

    client = TestClient(app)

    # 1. POST /api/v1/runs/{run_id}/diagnose
    resp = client.post(f"/api/v1/runs/{run.run_id}/diagnose")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run.run_id
    assert "root_cause_summary" in data
    assert "reproduction_steps" in data
    assert "regression_test_spec" in data
    diag_id = data["diagnosis_id"]

    # 2. GET /api/v1/runs/{run_id}/diagnosis
    resp2 = client.get(f"/api/v1/runs/{run.run_id}/diagnosis")
    assert resp2.status_code == 200
    assert resp2.json()["diagnosis_id"] == diag_id

    # 3. GET /api/v1/diagnoses
    resp3 = client.get("/api/v1/diagnoses")
    assert resp3.status_code == 200
    assert len(resp3.json()) >= 1

    app.dependency_overrides.clear()
