import asyncio
import tempfile
import os
from pathlib import Path
import pytest

from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.execution.playwright_runner import PlaywrightTestRunner
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.services.run_manager import RunManager
from backend.app.models import (
    ApplicationTarget,
    TestRun,
    TestRunCreate,
    TestMode,
    RunStatus,
    RunnerType,
    ActionType,
    ActionStatus,
    FailureCategory,
)

@pytest.fixture
def playwright_test_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_playwright.db")
    artifacts_dir = Path(temp_dir) / "artifacts"
    
    repo = SQLiteRepository(db_path=db_path)
    blob_storage = LocalEvidenceBlobStorage(base_dir=artifacts_dir)
    
    runner = PlaywrightTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=blob_storage,
    )
    
    # Create a local file target for deterministic local testing
    html_file = Path(temp_dir) / "test_target.html"
    html_file.write_text("""
    <!DOCTYPE html>
    <html>
    <head><title>Antigravity Local Target App</title></head>
    <body style="background:#0b1120; color:white; font-family:sans-serif;">
        <h1 id="main-title">Antigravity Local Target</h1>
        <div id="content-container">
            <input type="text" id="username" name="username" placeholder="Enter username" />
            <button id="submit-btn" onclick="console.log('Button clicked!')">Submit</button>
        </div>
        <script>
            console.log('Page initialized successfully.');
        </script>
    </body>
    </html>
    """, encoding="utf-8")

    target = ApplicationTarget(
        target_id="tgt_local_fixture",
        name="Local Test HTML Fixture",
        base_url=f"file:///{html_file.as_posix()}",
    )
    repo.create_target(target)

    yield repo, blob_storage, runner, target

    # Cleanup


def test_playwright_runner_successful_execution(playwright_test_env):
    repo, blob_storage, runner, target = playwright_test_env

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.PLAYWRIGHT,
    )
    repo.create_run(run)

    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.PLAYWRIGHT,
        simulate_failure=False,
    )

    result_run = asyncio.run(runner.execute(run, target, options))

    # 1. Verify Run Status & Isolation
    assert result_run.status == RunStatus.PASSED
    assert result_run.runner_type == RunnerType.PLAYWRIGHT
    assert result_run.browser_context_id is not None
    assert result_run.session_id is not None
    assert len(result_run.actions) == 5
    assert len(result_run.failure_ids) == 0

    # 2. Verify Structured Evidence was recorded
    evidence_items = repo.get_evidence_by_run(result_run.run_id)
    assert len(evidence_items) >= 4

    # Check DOM Snapshot Artifact
    dom_evis = [e for e in evidence_items if e.evidence_type.value == "DOM_SNAPSHOT"]
    assert len(dom_evis) == 1
    assert dom_evis[0].artifact_path is not None
    assert Path(dom_evis[0].artifact_path).exists()
    dom_content = Path(dom_evis[0].artifact_path).read_text(encoding="utf-8")
    assert "Antigravity Local Target" in dom_content

    # Check Screenshot Artifact
    screenshot_evis = [e for e in evidence_items if e.evidence_type.value == "SCREENSHOT"]
    assert len(screenshot_evis) == 1
    assert screenshot_evis[0].artifact_path is not None
    assert Path(screenshot_evis[0].artifact_path).exists()
    screenshot_bytes = Path(screenshot_evis[0].artifact_path).read_bytes()
    assert len(screenshot_bytes) > 500 # valid PNG file
    assert screenshot_evis[0].mime_type == "image/png"

    # Check Console Logs Artifact
    console_evis = [e for e in evidence_items if e.evidence_type.value == "CONSOLE_LOG"]
    assert len(console_evis) == 1
    assert console_evis[0].artifact_path is not None
    assert Path(console_evis[0].artifact_path).exists()


def test_playwright_runner_deterministic_failure(playwright_test_env):
    repo, blob_storage, runner, target = playwright_test_env

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.PLAYWRIGHT,
    )
    repo.create_run(run)

    # Trigger failure simulation
    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        runner_type=RunnerType.PLAYWRIGHT,
        simulate_failure=True,
    )

    result_run = asyncio.run(runner.execute(run, target, options))

    assert result_run.status == RunStatus.FAILED
    assert len(result_run.failure_ids) == 1

    failures = repo.get_failures_by_run(result_run.run_id)
    assert len(failures) == 1
    assert failures[0].category == FailureCategory.ASSERTION_FAILED
    assert "Element '#non-existent-required-token' was not found" in failures[0].message
    assert failures[0].stack_trace is not None


def test_run_manager_runner_routing(playwright_test_env):
    repo, blob_storage, playwright_runner, target = playwright_test_env

    mock_runner = MockTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
    )

    manager = RunManager(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        runners={
            RunnerType.MOCK: mock_runner,
            RunnerType.PLAYWRIGHT: playwright_runner,
        },
    )

    # 1. Test Mock Routing (Backwards compatibility)
    mock_payload = TestRunCreate(
        application_id=target.target_id,
        runner_type=RunnerType.MOCK,
        action_delay_ms=0,
    )
    mock_run = asyncio.run(manager.initiate_run(mock_payload))
    assert mock_run.runner_type == RunnerType.MOCK
    assert mock_run.status == RunStatus.PASSED

    # 2. Test Playwright Routing
    pw_payload = TestRunCreate(
        application_id=target.target_id,
        runner_type=RunnerType.PLAYWRIGHT,
        action_delay_ms=0,
    )
    pw_run = asyncio.run(manager.initiate_run(pw_payload))
    assert pw_run.runner_type == RunnerType.PLAYWRIGHT
    assert pw_run.browser_context_id is not None
    assert pw_run.status == RunStatus.PASSED
