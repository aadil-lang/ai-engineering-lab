import tempfile
import os
import pytest
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.models import (
    ApplicationTarget,
    TestRun,
    TestRunCreate,
    TestMode,
    RunStatus,
    ActionType,
    ActionStatus,
)

@pytest.fixture
def test_setup():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    repo = SQLiteRepository(db_path=db_path)
    runner = MockTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
    )
    target = ApplicationTarget(
        name="Mock Target",
        base_url="https://mock.example.com",
    )
    repo.create_target(target)
    yield repo, runner, target
    if os.path.exists(db_path):
        os.remove(db_path)

import asyncio

def test_mock_runner_success_flow(test_setup):
    repo, runner, target = test_setup
    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
    )
    repo.create_run(run)

    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        simulate_failure=False,
        action_delay_ms=0, # Fast execution in tests
    )

    result_run = asyncio.run(runner.execute(run, target, options))

    assert result_run.status == RunStatus.PASSED
    assert len(result_run.actions) == 5
    assert len(result_run.evidence_ids) == 5
    assert len(result_run.failure_ids) == 0
    assert result_run.actions[0].action_type == ActionType.NAVIGATE
    assert result_run.actions[4].action_type == ActionType.SUBMIT
    assert result_run.actions[0].status == ActionStatus.PASSED

def test_mock_runner_simulated_failure(test_setup):
    repo, runner, target = test_setup
    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
    )
    repo.create_run(run)

    options = TestRunCreate(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        simulate_failure=True,
        action_delay_ms=0,
    )

    result_run = asyncio.run(runner.execute(run, target, options))

    assert result_run.status == RunStatus.FAILED
    assert len(result_run.failure_ids) == 1
    # Check failure record details
    failures = repo.get_failures_by_run(result_run.run_id)
    assert len(failures) == 1
    assert failures[0].severity.value == "HIGH"
    assert failures[0].suggested_remediation is not None
