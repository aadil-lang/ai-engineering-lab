import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json

from backend.app.main import app
from backend.app.models.diagnosis import EngineeringDiagnosis, DeterministicSignal, ReproductionStep
from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician
from backend.app.models.remediation import (
    RemediationTask,
    CodeChange,
    FileChange,
    RemediationAttempt,
    RegressionVerification,
)
from backend.app.models.enums import RemediationStatus, FileChangeOperation, FailureCategory, Severity, RunStatus, TestMode, RunnerType
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget, ApplicationTargetCreate
from backend.app.models.test_case import TestCaseCreate
from backend.app.remediation.coding_agent import MockCodingAgent, OllamaCodingAgent
from backend.app.remediation.workspace import RemediationWorkspace
from backend.app.services.remediation_service import RemediationService
from backend.app.services.run_manager import RunManager
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.execution.mock_runner import MockTestRunner

client = TestClient(app)

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock source file
        sample_file = Path(tmpdir) / "src" / "App.py"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text("def handle_action():\n    return False\n", encoding="utf-8")
        yield tmpdir

@pytest.fixture
def repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    return SQLiteRepository(db_path=db_path)

import asyncio

def test_mock_coding_agent_propose_change():
    agent = MockCodingAgent()
    diagnosis = EngineeringDiagnosis(
        run_id="run_test_123",
        failure_id="fail_123",
        title="Element not clickable due to overlay",
        root_cause_summary="A modal overlay was not dismissed before attempting click",
        failure_category=FailureCategory.ELEMENT_NOT_INTERACTABLE,
        confidence_score=0.95,
        suspected_component="src/components/Modal.tsx",
        deterministic_signals=[],
        reproduction_steps=[],
        suggested_fix="Dismiss modal overlay before click event",
        code_diff_suggestion="--- a/Modal.tsx\n+++ b/Modal.tsx\n@@ -1 +1 @@\n-visible\n+hidden",
        regression_test_spec="test('modal dismiss', () => {});",
        severity=Severity.HIGH,
    )

    code_change = asyncio.run(agent.propose_change(
        repository="local_workspace",
        diagnosis=diagnosis,
        task_id="rem_123",
    ))

    assert code_change.task_id == "rem_123"
    assert "Modal.tsx" in code_change.files[0].path
    assert code_change.files[0].operation == FileChangeOperation.MODIFY
    assert "Dismiss modal overlay" in code_change.summary
    assert len(code_change.tests_to_run) > 0

def test_remediation_workspace_patch_and_rollback(temp_workspace):
    ws = RemediationWorkspace(workspace_root=temp_workspace)
    
    file_change = FileChange(
        path="src/App.py",
        operation=FileChangeOperation.MODIFY,
        new_content="def handle_action():\n    return True\n",
    )

    # 1. Apply valid patch
    res = ws.apply_changes([file_change])
    assert res["success"] is True
    assert (Path(temp_workspace) / "src" / "App.py").read_text(encoding="utf-8") == "def handle_action():\n    return True\n"

    # 2. Apply invalid python syntax -> should trigger rollback
    invalid_change = FileChange(
        path="src/App.py",
        operation=FileChangeOperation.MODIFY,
        new_content="def invalid_syntax(\n",
    )
    bad_res = ws.apply_changes([invalid_change])
    assert bad_res["success"] is False
    assert "SyntaxError" in bad_res["error"]

    # 3. Verify rollback restored original state
    ws.rollback()
    assert (Path(temp_workspace) / "src" / "App.py").read_text(encoding="utf-8") == "def handle_action():\n    return False\n"

def test_remediation_service_closed_loop(repo, temp_workspace):
    async def _run_test():
        # Setup test target and run
        target = repo.create_target(
            ApplicationTarget(
                target_id="app_target_remed",
                name="Remediation Target",
                target_type="WEB_APPLICATION",
                base_url="http://localhost:3000",
                environment="TEST",
                version="1.0.0",
            )
        )

        mock_runner = MockTestRunner(repo, repo, repo, repo)
        run_manager = RunManager(
            run_repo=repo,
            target_repo=repo,
            test_case_repo=repo,
            evidence_repo=repo,
            failure_repo=repo,
            metric_repo=repo,
            runner=mock_runner,
        )

        # Create a failed run
        failed_payload = TestRunCreate(
            application_id=target.target_id,
            test_mode=TestMode.FUNCTIONAL_QA,
            simulate_failure=True,
        )
        failed_run = await run_manager.initiate_run(failed_payload)
        assert failed_run.status == RunStatus.FAILED

        # Initialize RemediationService
        coding_agent = MockCodingAgent()
        diagnostician = QwenDiagnostician(base_url="http://localhost:99999")
        diagnosis_service = DiagnosisService(repo, repo, repo, repo, repo, diagnostician=diagnostician)
        ws = RemediationWorkspace(workspace_root=temp_workspace)
        service = RemediationService(
            remediation_repo=repo,
            run_repo=repo,
            diagnosis_repo=repo,
            evidence_repo=repo,
            target_repo=repo,
            coding_agent=coding_agent,
            diagnosis_service=diagnosis_service,
            run_manager=run_manager,
            workspace=ws,
        )

        # 1. Create remediation task
        task = await service.create_remediation_task(run_id=failed_run.run_id)
        assert task.status == RemediationStatus.PROPOSED
        assert len(task.code_changes) == 1
        assert task.run_id == failed_run.run_id

        # 2. Apply & verify
        resolved_task = await service.apply_and_verify(task.task_id)
        assert resolved_task.status == RemediationStatus.RESOLVED
        assert len(resolved_task.attempts) == 1
        assert resolved_task.attempts[0].status == RemediationStatus.RESOLVED
        assert len(resolved_task.verifications) == 1
        assert resolved_task.verifications[0].failed_before is True
        assert resolved_task.verifications[0].failed_after is False

    asyncio.run(_run_test())


def test_remediation_api_endpoints():
    from backend.app.api.deps import get_coding_agent, get_diagnosis_service, get_repository
    repo = SQLiteRepository()
    diagnostician = QwenDiagnostician(base_url="http://localhost:99999")
    app.dependency_overrides[get_coding_agent] = lambda: MockCodingAgent()
    app.dependency_overrides[get_diagnosis_service] = lambda: DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=diagnostician,
    )

    try:
        # 1. Create target
        target_resp = client.post(
            "/api/v1/targets",
            json={
                "name": "API Remediation App",
                "target_type": "WEB_APPLICATION",
                "base_url": "http://localhost:3000",
                "environment": "TEST",
                "version": "1.0.0",
            },
        )
        assert target_resp.status_code == 201
        target_id = target_resp.json()["target_id"]

        # 2. Create failing run
        run_resp = client.post(
            "/api/v1/runs",
            json={
                "application_id": target_id,
                "test_mode": "FUNCTIONAL_QA",
                "simulate_failure": True,
            },
        )
        assert run_resp.status_code == 201
        run_id = run_resp.json()["run_id"]

        # 3. Request remediation via API
        remed_resp = client.post(f"/api/v1/runs/{run_id}/remediate")
        assert remed_resp.status_code == 200, f"Failed: {remed_resp.text}"
        task_data = remed_resp.json()
        assert task_data["run_id"] == run_id
        assert task_data["status"] == "PROPOSED"
        assert len(task_data["code_changes"]) > 0
        task_id = task_data["task_id"]

        # 4. Apply and verify via API
        verify_resp = client.post(f"/api/v1/remediations/{task_id}/apply-verify")
        assert verify_resp.status_code == 200, f"Failed: {verify_resp.text}"
        verify_data = verify_resp.json()
        assert verify_data["status"] == "RESOLVED"
        assert len(verify_data["verifications"]) > 0

        # 5. Fetch remediation detail
        detail_resp = client.get(f"/api/v1/remediations/{task_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["task_id"] == task_id

        # 6. List remediations
        list_resp = client.get("/api/v1/remediations")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1
    finally:
        app.dependency_overrides.clear()


