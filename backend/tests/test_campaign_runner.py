import pytest
import asyncio
from datetime import datetime, timezone

from backend.app.models.enums import (
    CampaignStatus,
    RunnerType,
    ExecutionSource,
    RunStatus,
    TestMode,
    TargetType,
)
from backend.app.models.campaign import (
    Campaign,
    CampaignConfiguration,
    CampaignCreate,
)
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.services.run_manager import RunManager
from backend.app.services.campaign_service import CampaignService
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def temp_repo(tmp_path):
    db_file = tmp_path / "test_campaign.db"
    return SQLiteRepository(db_path=str(db_file))


@pytest.fixture
def mock_run_manager(temp_repo):
    target = ApplicationTarget(
        target_id="tgt_campaign_test",
        name="Campaign Test Target",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://localhost:8000",
        environment="test",
        version="1.0.0",
    )
    temp_repo.create_target(target)

    tc = TestCase(
        test_case_id="tc_campaign_test",
        target_id=target.target_id,
        name="Campaign Smoke Test",
        test_mode=TestMode.FUNCTIONAL_QA,
        steps=[{"type": "NAVIGATE", "target": "http://localhost:8000"}],
    )
    temp_repo.create_test_case(tc)

    mock_runner = MockTestRunner(
        run_repo=temp_repo,
        evidence_repo=temp_repo,
        failure_repo=temp_repo,
        metric_repo=temp_repo,
    )

    return RunManager(
        run_repo=temp_repo,
        target_repo=temp_repo,
        test_case_repo=temp_repo,
        evidence_repo=temp_repo,
        failure_repo=temp_repo,
        metric_repo=temp_repo,
        runners={
            RunnerType.MOCK: mock_runner,
            RunnerType.PLAYWRIGHT: mock_runner,
        },
    )


def test_campaign_model_creation():
    config = CampaignConfiguration(
        target_id="tgt_test",
        test_case_ids=["tc_1"],
        iterations_per_test_case=2,
    )
    campaign = Campaign(
        name="Test Campaign",
        target_id="tgt_test",
        configuration=config,
        status=CampaignStatus.CREATED,
    )
    assert campaign.status == CampaignStatus.CREATED
    assert campaign.name == "Test Campaign"
    assert campaign.campaign_id.startswith("camp_")
    assert campaign.completed_runs == 0


def test_sqlite_campaign_repository_crud(temp_repo):
    config = CampaignConfiguration(
        target_id="tgt_repo_test",
        test_case_ids=["tc_1"],
        runner_types=[RunnerType.MOCK],
        iterations_per_test_case=3,
    )
    campaign = Campaign(
        campaign_id="camp_test_123",
        name="Repo Test Campaign",
        target_id="tgt_repo_test",
        configuration=config,
        status=CampaignStatus.CREATED,
        requested_runs=3,
    )

    # Create
    created = temp_repo.create_campaign(campaign)
    assert created.campaign_id == "camp_test_123"

    # Get
    fetched = temp_repo.get_campaign("camp_test_123")
    assert fetched is not None
    assert fetched.name == "Repo Test Campaign"
    assert fetched.requested_runs == 3

    # Update
    fetched.status = CampaignStatus.RUNNING
    fetched.completed_runs = 1
    fetched.passed_runs = 1
    temp_repo.update_campaign(fetched)

    updated = temp_repo.get_campaign("camp_test_123")
    assert updated.status == CampaignStatus.RUNNING
    assert updated.completed_runs == 1

    # List & Count
    all_camps = temp_repo.list_campaigns()
    assert len(all_camps) >= 1
    assert temp_repo.count_campaigns() >= 1


def test_test_run_campaign_id_association(temp_repo, mock_run_manager):
    target = temp_repo.get_target("tgt_campaign_test")
    run_req = TestRunCreate(
        application_id=target.target_id,
        test_case_id="tc_campaign_test",
        runner_type=RunnerType.MOCK,
        campaign_id="camp_custom_001",
    )

    run = asyncio.run(mock_run_manager.initiate_run(run_req))
    assert run.campaign_id == "camp_custom_001"

    # Verify retrieval from repository
    retrieved = temp_repo.get_run(run.run_id)
    assert retrieved.campaign_id == "camp_custom_001"

    # Verify filtering by campaign_id
    campaign_runs = temp_repo.get_runs_by_campaign("camp_custom_001")
    assert len(campaign_runs) == 1
    assert campaign_runs[0].run_id == run.run_id


def test_campaign_service_sequential_execution(temp_repo, mock_run_manager):
    service = CampaignService(
        campaign_repo=temp_repo,
        run_manager=mock_run_manager,
        target_repo=temp_repo,
        test_case_repo=temp_repo,
    )

    create_req = CampaignCreate(
        name="Sequential 3-Run Campaign",
        target_id="tgt_campaign_test",
        test_case_ids=["tc_campaign_test"],
        runner_types=[RunnerType.MOCK],
        iterations_per_test_case=3,
        delay_between_runs_ms=10,
    )

    campaign = service.create_campaign(create_req)
    assert campaign.requested_runs == 3
    assert campaign.status == CampaignStatus.CREATED

    # Execute
    completed = asyncio.run(service.execute_campaign(campaign.campaign_id))
    assert completed.status == CampaignStatus.COMPLETED
    assert completed.completed_runs == 3
    assert completed.passed_runs == 3
    assert completed.failed_runs == 0
    assert len(completed.run_ids) == 3

    # Check report
    report = completed.summary_report
    assert report["total_requested"] == 3
    assert report["total_completed"] == 3
    assert report["passed_count"] == 3
    assert report["pass_rate"] == 1.0
    assert "population_impact" in report


def test_campaign_service_stop_on_first_failure(temp_repo):
    target = ApplicationTarget(
        target_id="tgt_fail_test",
        name="Fail Target",
        target_type=TargetType.WEB_APPLICATION,
        base_url="http://localhost:8000",
        environment="test",
        version="1.0.0",
    )
    temp_repo.create_target(target)

    tc = TestCase(
        test_case_id="tc_fail_test",
        target_id=target.target_id,
        name="Failing Test",
        test_mode=TestMode.FUNCTIONAL_QA,
        steps=[{"type": "NAVIGATE", "target": "http://localhost:8000"}],
    )
    temp_repo.create_test_case(tc)

    # Use mock runner with simulate_failure parameter
    mock_runner = MockTestRunner(
        run_repo=temp_repo,
        evidence_repo=temp_repo,
        failure_repo=temp_repo,
        metric_repo=temp_repo,
    )
    run_mgr = RunManager(
        run_repo=temp_repo,
        target_repo=temp_repo,
        test_case_repo=temp_repo,
        evidence_repo=temp_repo,
        failure_repo=temp_repo,
        metric_repo=temp_repo,
        runners={RunnerType.MOCK: mock_runner},
    )
    service = CampaignService(
        campaign_repo=temp_repo,
        run_manager=run_mgr,
        target_repo=temp_repo,
        test_case_repo=temp_repo,
    )

    create_req = CampaignCreate(
        name="Early Stop Campaign",
        target_id="tgt_fail_test",
        test_case_ids=["tc_fail_test"],
        runner_types=[RunnerType.MOCK],
        iterations_per_test_case=5,
        stop_on_first_failure=True,
        delay_between_runs_ms=5,
        parameters={"simulate_failure": True, "action_delay_ms": 5},
    )

    campaign = service.create_campaign(create_req)
    completed = asyncio.run(service.execute_campaign(campaign.campaign_id))

    assert completed.status == CampaignStatus.PARTIAL
    assert completed.completed_runs == 1
    assert completed.failed_runs == 1
    assert completed.cancelled_runs == 4
    assert "First failure encountered" in completed.summary_report["early_stop_reason"]


def test_api_campaign_endpoints(temp_repo, mock_run_manager):
    from backend.app.api import deps
    service = CampaignService(
        campaign_repo=temp_repo,
        run_manager=mock_run_manager,
        target_repo=temp_repo,
        test_case_repo=temp_repo,
    )
    app.dependency_overrides[deps.get_campaign_service] = lambda: service

    try:
        client = TestClient(app)

        # 1. Create and execute campaign synchronously
        create_payload = {
            "name": "API Test Campaign",
            "target_id": "tgt_campaign_test",
            "test_case_ids": ["tc_campaign_test"],
            "runner_types": ["MOCK"],
            "iterations_per_test_case": 2,
            "delay_between_runs_ms": 10,
        }
        resp = client.post("/api/v1/campaigns/?execute_async=false", json=create_payload)
        assert resp.status_code == 201
        data = resp.json()
        camp_id = data["campaign_id"]
        assert data["status"] == "COMPLETED"
        assert data["completed_runs"] == 2

        # 2. List campaigns
        resp = client.get("/api/v1/campaigns/")
        assert resp.status_code == 200
        camps = resp.json()
        assert len(camps) >= 1
        assert any(c["campaign_id"] == camp_id for c in camps)

        # 3. Get campaign details
        resp = client.get(f"/api/v1/campaigns/{camp_id}")
        assert resp.status_code == 200
        assert resp.json()["campaign_id"] == camp_id

        # 4. Get campaign runs
        resp = client.get(f"/api/v1/campaigns/{camp_id}/runs")
        assert resp.status_code == 200
        runs = resp.json()
        assert len(runs) == 2
        assert all(r["campaign_id"] == camp_id for r in runs)

        # 5. Get campaign report
        resp = client.get(f"/api/v1/campaigns/{camp_id}/report")
        assert resp.status_code == 200
        report = resp.json()
        assert report["campaign_id"] == camp_id
        assert report["total_completed"] == 2
        assert report["pass_rate"] == 1.0
    finally:
        app.dependency_overrides.clear()

