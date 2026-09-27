import tempfile
import os
import pytest
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.models import (
    ApplicationTarget,
    TestCase,
    TestRun,
    TestAction,
    Evidence,
    Failure,
    Metric,
    TestMode,
    RunStatus,
    ActionType,
    ActionStatus,
    EvidenceType,
    FailureCategory,
    Severity,
)

@pytest.fixture
def temp_repo():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    repo = SQLiteRepository(db_path=db_path)
    yield repo
    if os.path.exists(db_path):
        os.remove(db_path)

def test_target_crud(temp_repo):
    target = ApplicationTarget(
        name="Mock E-Commerce",
        base_url="http://mock-shop.local",
    )
    saved = temp_repo.create_target(target)
    assert saved.target_id == target.target_id

    retrieved = temp_repo.get_target(target.target_id)
    assert retrieved is not None
    assert retrieved.name == "Mock E-Commerce"

    all_targets = temp_repo.list_targets()
    assert len(all_targets) == 1

def test_run_and_evidence_crud(temp_repo):
    run = TestRun(
        application_id="tgt_123",
        test_mode=TestMode.FUNCTIONAL_QA,
        status=RunStatus.RUNNING,
    )
    temp_repo.create_run(run)

    # Evidence
    evi = Evidence(
        run_id=run.run_id,
        evidence_type=EvidenceType.DOM_SNAPSHOT,
        title="Page Snapshot",
        payload={"html": "<div>content</div>"},
    )
    temp_repo.save_evidence(evi)

    # Failure
    fail = Failure(
        run_id=run.run_id,
        category=FailureCategory.FUNCTIONAL_BUG,
        severity=Severity.HIGH,
        title="Crash",
        message="500 Internal Error",
    )
    temp_repo.save_failure(fail)

    # Metric
    met = Metric(
        run_id=run.run_id,
        name="latency",
        value=54.2,
        unit="ms",
    )
    temp_repo.save_metric(met)

    # Update run
    run.status = RunStatus.PASSED
    run.duration_ms = 450
    run.evidence_ids.append(evi.evidence_id)
    temp_repo.update_run(run)

    fetched_run = temp_repo.get_run(run.run_id)
    assert fetched_run.status == RunStatus.PASSED
    assert fetched_run.duration_ms == 450
    assert evi.evidence_id in fetched_run.evidence_ids

    evidence_list = temp_repo.get_evidence_by_run(run.run_id)
    assert len(evidence_list) == 1
    assert evidence_list[0].title == "Page Snapshot"

    failures = temp_repo.get_failures_by_run(run.run_id)
    assert len(failures) == 1

    metrics = temp_repo.get_metrics_by_run(run.run_id)
    assert len(metrics) == 1
    assert metrics[0].value == 54.2
