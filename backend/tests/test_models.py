import pytest
from backend.app.models import (
    TestMode,
    RunStatus,
    ActionType,
    ActionStatus,
    EvidenceType,
    FailureCategory,
    Severity,
    AssessmentDimension,
    TargetType,
    ApplicationTarget,
    TestAction,
    Evidence,
    Failure,
    Metric,
    TestRun,
    TestCase,
    Assessment,
    Environment,
)

def test_model_instantiations():
    target = ApplicationTarget(
        name="Test Target",
        target_type=TargetType.WEB_APPLICATION,
        base_url="https://test.example.com",
    )
    assert target.target_id.startswith("tgt_")
    assert target.environment == "staging"

    action = TestAction(
        action_type=ActionType.NAVIGATE,
        description="Navigating to home",
        status=ActionStatus.PASSED,
        input_data={"url": "https://test.example.com"},
        duration_ms=120,
    )
    assert action.action_id.startswith("act_")

    evidence = Evidence(
        run_id="run_123",
        action_id=action.action_id,
        evidence_type=EvidenceType.DOM_SNAPSHOT,
        title="Home DOM",
        payload={"dom": "<html></html>"},
    )
    assert evidence.evidence_id.startswith("evi_")

    failure = Failure(
        run_id="run_123",
        action_id=action.action_id,
        category=FailureCategory.ASSERTION_FAILURE,
        severity=Severity.HIGH,
        title="Check failed",
        message="Expected title not found",
    )
    assert failure.failure_id.startswith("fail_")

    metric = Metric(
        run_id="run_123",
        name="load_time_ms",
        value=145.2,
        unit="ms",
    )
    assert metric.metric_id.startswith("met_")

    run = TestRun(
        application_id=target.target_id,
        test_mode=TestMode.FUNCTIONAL_QA,
        status=RunStatus.RUNNING,
        actions=[action],
        evidence_ids=[evidence.evidence_id],
        failure_ids=[failure.failure_id],
    )
    assert run.run_id.startswith("run_")
    assert len(run.actions) == 1
    assert run.actions[0].action_type == ActionType.NAVIGATE
