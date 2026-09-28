import pytest
import asyncio
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import base64

from backend.app.main import app
from backend.app.dogfooding.live_session_models import LiveDogfoodingSession, LiveSessionStatus
from backend.app.dogfooding.live_events import LiveEvent, LiveEventType
from backend.app.dogfooding.live_session_bus import LiveSessionEventBus, live_event_bus
from backend.app.dogfooding.runner_observer import LiveRunnerObserver
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget
from backend.app.models.enums import RunnerType, ExecutionSource, TestMode, RunStatus

@pytest.fixture
def fresh_bus():
    """Provides an isolated clean LiveSessionEventBus for unit testing."""
    return LiveSessionEventBus()

@pytest.fixture
def client():
    return TestClient(app)

# ═══════════════════════════════════════════════════════════════════════
# 1. Domain Models & Lifecycle States
# ═══════════════════════════════════════════════════════════════════════

def test_01_live_session_model_creation():
    """Verifies all mandatory fields are present and typed on LiveDogfoodingSession."""
    session = LiveDogfoodingSession(
        run_id="run_test_01",
        target_id="target_qg",
        application_id="question_generator",
        test_case_id="tc_smoke",
        runner_type=RunnerType.PLAYWRIGHT,
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
        total_steps=10,
    )
    assert session.session_id.startswith("sess_live_")
    assert session.run_id == "run_test_01"
    assert session.application_id == "question_generator"
    assert session.status == LiveSessionStatus.CREATED
    assert session.current_step == 0
    assert session.total_steps == 10
    assert session.latest_event_sequence == 0
    assert session.subscriber_count == 0
    assert session.created_at is not None

def test_02_live_session_lifecycle_states(fresh_bus):
    """Verifies valid state transitions: CREATED -> RUNNING -> COMPLETED."""
    sess = fresh_bus.create_session(
        run_id="run_lifecycle",
        target_id="target_01",
        application_id="app_01",
    )
    assert sess.status == LiveSessionStatus.CREATED

    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED, {"target_url": "http://localhost:3000"})
    assert sess.status == LiveSessionStatus.RUNNING
    assert sess.started_at is not None

    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_COMPLETED, {"status": "PASSED"})
    assert sess.status == LiveSessionStatus.COMPLETED
    assert sess.finished_at is not None

def test_03_live_session_cancellation(fresh_bus):
    """Verifies cancelling an active live session transitions status to CANCELLED."""
    sess = fresh_bus.create_session(
        run_id="run_cancel",
        target_id="target_01",
        application_id="app_01",
    )
    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)
    assert sess.status == LiveSessionStatus.RUNNING

    cancelled = fresh_bus.cancel_session(sess.session_id, reason="User clicked cancel")
    assert cancelled.status == LiveSessionStatus.CANCELLED
    assert cancelled.finished_at is not None

def test_04_live_session_failure(fresh_bus):
    """Verifies session failure transitions status to FAILED."""
    sess = fresh_bus.create_session(
        run_id="run_fail",
        target_id="target_01",
        application_id="app_01",
    )
    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)
    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_FAILED, {"error": "Browser crashed"})
    assert sess.status == LiveSessionStatus.FAILED
    assert sess.finished_at is not None

# ═══════════════════════════════════════════════════════════════════════
# 2. Monotonic Sequencing & Event Architecture
# ═══════════════════════════════════════════════════════════════════════

def test_05_monotonic_sequence_numbering(fresh_bus):
    """Verifies that each event receives a strictly monotonically increasing sequence number."""
    sess = fresh_bus.create_session(
        run_id="run_seq",
        target_id="target_01",
        application_id="app_01",
    )
    # create_session emits sequence 1 (SESSION_CREATED)
    assert sess.latest_event_sequence == 1

    e2 = fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)
    assert e2.sequence_number == 2

    e3 = fresh_bus.publish(sess.session_id, LiveEventType.NAVIGATION_STARTED, {"url": "http://app.com"})
    assert e3.sequence_number == 3

    e4 = fresh_bus.publish(sess.session_id, LiveEventType.NAVIGATION_COMPLETED, {"url": "http://app.com"})
    assert e4.sequence_number == 4

    assert sess.latest_event_sequence == 4

def test_06_event_model_fields():
    """Verifies LiveEvent model has all required fields."""
    event = LiveEvent(
        session_id="sess_123",
        run_id="run_456",
        sequence_number=1,
        event_type=LiveEventType.ACTION_STARTED,
        payload={"action": "click", "selector": "#btn-submit"},
    )
    assert event.event_id.startswith("evt_")
    assert event.session_id == "sess_123"
    assert event.run_id == "run_456"
    assert event.sequence_number == 1
    assert event.event_type == LiveEventType.ACTION_STARTED
    assert event.timestamp is not None
    assert event.payload["action"] == "click"

def test_07_all_required_event_types_supported():
    """Verifies all required event types from specification exist."""
    required = [
        "SESSION_CREATED", "SESSION_STARTED", "NAVIGATION_STARTED", "NAVIGATION_COMPLETED",
        "DOM_OBSERVED", "ACTION_STARTED", "ACTION_COMPLETED", "ACTION_FAILED",
        "SCREENSHOT_CAPTURED", "CONSOLE_EVENT", "PAGE_ERROR",
        "NETWORK_REQUEST_STARTED", "NETWORK_REQUEST_COMPLETED", "NETWORK_REQUEST_FAILED",
        "PERFORMANCE_UPDATE", "ASSERTION_STARTED", "ASSERTION_PASSED", "ASSERTION_FAILED",
        "EVIDENCE_CAPTURED", "DETERMINISTIC_EVALUATION_STARTED", "DETERMINISTIC_EVALUATION_COMPLETED",
        "DIAGNOSIS_STARTED", "DIAGNOSIS_COMPLETED", "REMEDIATION_PROPOSED", "GOVERNANCE_REQUIRED",
        "RETEST_STARTED", "RETEST_COMPLETED", "SESSION_COMPLETED", "SESSION_FAILED", "SESSION_CANCELLED",
    ]
    for r in required:
        assert hasattr(LiveEventType, r), f"Missing required LiveEventType: {r}"

def test_08_event_bus_publish_and_history(fresh_bus):
    """Verifies event history buffer stores all published events."""
    sess = fresh_bus.create_session("run_hist", "target_01", "app_01")
    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)
    fresh_bus.publish(sess.session_id, LiveEventType.DOM_OBSERVED, {"element_count": 25})

    events = fresh_bus.get_events(sess.session_id)
    assert len(events) == 3
    assert events[0].event_type == LiveEventType.SESSION_CREATED
    assert events[1].event_type == LiveEventType.SESSION_STARTED
    assert events[2].event_type == LiveEventType.DOM_OBSERVED

def test_09_gapless_replay_from_sequence(fresh_bus):
    """Verifies querying from_sequence returns only subsequent events."""
    sess = fresh_bus.create_session("run_replay", "target_01", "app_01")
    fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED) # seq 2
    fresh_bus.publish(sess.session_id, LiveEventType.ACTION_STARTED, {"step": 1}) # seq 3
    fresh_bus.publish(sess.session_id, LiveEventType.ACTION_COMPLETED, {"step": 1}) # seq 4

    replayed = fresh_bus.get_events(sess.session_id, from_sequence=2)
    assert len(replayed) == 2
    assert replayed[0].sequence_number == 3
    assert replayed[1].sequence_number == 4

def test_10_pub_sub_broadcasting(fresh_bus):
    """Verifies subscribers receive real-time events published to the session."""
    sess = fresh_bus.create_session("run_sub", "target_01", "app_01")

    received = []
    async def run_async():
        async def sub_task():
            async for evt in fresh_bus.subscribe(sess.session_id, from_sequence=0):
                received.append(evt)
                if evt.event_type == LiveEventType.SESSION_COMPLETED:
                    break

        task = asyncio.create_task(sub_task())
        await asyncio.sleep(0.01)

        fresh_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)
        fresh_bus.publish(sess.session_id, LiveEventType.ACTION_STARTED, {"action": "click"})
        fresh_bus.publish(sess.session_id, LiveEventType.SESSION_COMPLETED)

        await task

    asyncio.run(run_async())
    assert len(received) == 4 # CREATED, STARTED, ACTION_STARTED, COMPLETED
    assert received[-1].event_type == LiveEventType.SESSION_COMPLETED

def test_11_subscriber_count_tracking(fresh_bus):
    """Verifies subscriber_count updates dynamically upon subscribe and disconnect."""
    sess = fresh_bus.create_session("run_sub_cnt", "target_01", "app_01")
    assert sess.subscriber_count == 0

    async def run_async():
        async def sub_client():
            async for evt in fresh_bus.subscribe(sess.session_id):
                if evt.event_type == LiveEventType.SESSION_COMPLETED:
                    break

        task1 = asyncio.create_task(sub_client())
        await asyncio.sleep(0.01)
        assert sess.subscriber_count == 1

        task2 = asyncio.create_task(sub_client())
        await asyncio.sleep(0.01)
        assert sess.subscriber_count == 2

        # End session to release subscribers
        fresh_bus.publish(sess.session_id, LiveEventType.SESSION_COMPLETED)
        await asyncio.gather(task1, task2)
        await asyncio.sleep(0.01)
        assert sess.subscriber_count == 0

    asyncio.run(run_async())

def test_12_screenshot_storage_and_retrieval(fresh_bus):
    """Verifies binary screenshot caching in event bus."""
    sess = fresh_bus.create_session("run_sc", "target_01", "app_01")
    dummy_bytes = b"\x89PNG\r\n\x1a\n\x00dummy_png_bytes"
    fresh_bus.store_latest_screenshot(sess.session_id, dummy_bytes, "sc_01")

    retrieved = fresh_bus.get_latest_screenshot(sess.session_id)
    assert retrieved == dummy_bytes
    assert sess.latest_screenshot_id == "sc_01"

# ═══════════════════════════════════════════════════════════════════════
# 3. Runner Observer Adapter
# ═══════════════════════════════════════════════════════════════════════

def test_13_runner_observer_for_run_creates_session():
    """Verifies LiveRunnerObserver.for_run attaches to existing or creates new session."""
    run = TestRun(
        run_id="run_obs_01",
        application_id="real_app",
        runner_type=RunnerType.PLAYWRIGHT,
        execution_source=ExecutionSource.REAL_PLAYWRIGHT,
    )
    target = ApplicationTarget(
        target_id="target_real",
        name="Real App",
        target_type="WEB_APPLICATION",
        base_url="http://localhost:3000",
        environment="local",
        version="1.0.0",
        description="Test",
        metadata={},
        created_at="",
        updated_at="",
    )
    obs = LiveRunnerObserver.for_run(run, target, total_steps=12)
    assert obs.session_id is not None
    assert obs.run_id == "run_obs_01"

    sess = live_event_bus.get_session(obs.session_id)
    assert sess is not None
    assert sess.total_steps == 12

def test_14_observer_navigation_events():
    """Verifies on_navigation_start and on_navigation_complete."""
    run = TestRun(run_id="run_obs_nav", application_id="app_nav")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_navigation_start("http://localhost:3000/checkout")
    obs.on_navigation_complete("http://localhost:3000/checkout", title="Checkout Page")

    events = live_event_bus.get_events(obs.session_id)
    nav_events = [e for e in events if e.event_type in (LiveEventType.NAVIGATION_STARTED, LiveEventType.NAVIGATION_COMPLETED)]
    assert len(nav_events) == 2
    assert nav_events[0].payload["url"] == "http://localhost:3000/checkout"
    assert nav_events[1].payload["title"] == "Checkout Page"

def test_15_observer_dom_observation_events():
    """Verifies on_dom_observed emits structured DOM summary."""
    run = TestRun(run_id="run_obs_dom", application_id="app_dom")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_dom_observed(step_index=1, element_count=42, url="http://localhost:3000")
    events = live_event_bus.get_events(obs.session_id)
    dom_evt = [e for e in events if e.event_type == LiveEventType.DOM_OBSERVED][-1]
    assert dom_evt.payload["step_index"] == 1
    assert dom_evt.payload["element_count"] == 42

def test_16_observer_action_lifecycle():
    """Verifies on_action_start and on_action_complete."""
    run = TestRun(run_id="run_obs_act", application_id="app_act")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_action_start("click", "Click Generate button", step_index=2, selector="#generate-btn")
    obs.on_action_complete("click", "Click Generate button", step_index=2, status="PASSED", duration_ms=120)

    events = live_event_bus.get_events(obs.session_id)
    act_starts = [e for e in events if e.event_type == LiveEventType.ACTION_STARTED]
    act_completes = [e for e in events if e.event_type == LiveEventType.ACTION_COMPLETED]
    assert len(act_starts) >= 1
    assert act_starts[-1].payload["selector"] == "#generate-btn"
    assert len(act_completes) >= 1
    assert act_completes[-1].payload["duration_ms"] == 120

def test_17_observer_screenshot_event():
    """Verifies on_screenshot updates latest screenshot and emits base64 payload."""
    run = TestRun(run_id="run_obs_sc", application_id="app_sc")
    obs = LiveRunnerObserver.for_run(run)

    raw_bytes = b"real_screenshot_binary_png_data"
    obs.on_screenshot(raw_bytes, "sc_obs_01", step_index=3)

    # Bus binary cache
    assert live_event_bus.get_latest_screenshot(obs.session_id) == raw_bytes

    # Event payload has base64
    events = live_event_bus.get_events(obs.session_id)
    sc_evt = [e for e in events if e.event_type == LiveEventType.SCREENSHOT_CAPTURED][-1]
    assert sc_evt.payload["screenshot_id"] == "sc_obs_01"
    decoded = base64.b64decode(sc_evt.payload["screenshot_base64"])
    assert decoded == raw_bytes

def test_18_observer_console_and_page_error():
    """Verifies on_console and on_page_error events."""
    run = TestRun(run_id="run_obs_err", application_id="app_err")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_console({"type": "warn", "text": "Deprecated API"})
    obs.on_page_error("Uncaught TypeError: Cannot read property of undefined")

    events = live_event_bus.get_events(obs.session_id)
    c_evt = [e for e in events if e.event_type == LiveEventType.CONSOLE_EVENT][-1]
    p_evt = [e for e in events if e.event_type == LiveEventType.PAGE_ERROR][-1]
    assert c_evt.payload["text"] == "Deprecated API"
    assert "Uncaught TypeError" in p_evt.payload["error"]

def test_19_observer_network_events():
    """Verifies on_network_request and on_network_response."""
    run = TestRun(run_id="run_obs_net", application_id="app_net")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_network_request({"url": "http://api.com/items", "method": "POST"})
    obs.on_network_response({"url": "http://api.com/items", "status": 201, "ok": True})
    obs.on_network_response({"url": "http://api.com/error", "status": 500, "ok": False})

    events = live_event_bus.get_events(obs.session_id)
    reqs = [e for e in events if e.event_type == LiveEventType.NETWORK_REQUEST_STARTED]
    oks = [e for e in events if e.event_type == LiveEventType.NETWORK_REQUEST_COMPLETED]
    fails = [e for e in events if e.event_type == LiveEventType.NETWORK_REQUEST_FAILED]

    assert len(reqs) >= 1
    assert len(oks) >= 1
    assert len(fails) >= 1
    assert fails[-1].payload["status"] == 500

def test_20_observer_assertion_events():
    """Verifies on_assertion passed and failed."""
    run = TestRun(run_id="run_obs_asrt", application_id="app_asrt")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_assertion("Check title is present", passed=True)
    obs.on_assertion("Verify count equals 5", passed=False, detail="Expected 5 got 0")

    events = live_event_bus.get_events(obs.session_id)
    p_asrt = [e for e in events if e.event_type == LiveEventType.ASSERTION_PASSED][-1]
    f_asrt = [e for e in events if e.event_type == LiveEventType.ASSERTION_FAILED][-1]

    assert p_asrt.payload["passed"] is True
    assert f_asrt.payload["passed"] is False
    assert f_asrt.payload["detail"] == "Expected 5 got 0"

def test_21_observer_deterministic_evaluation():
    """Verifies on_deterministic_evaluation preserves authoritative status."""
    run = TestRun(run_id="run_obs_det", application_id="app_det")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_deterministic_evaluation("PASSED", {"evaluator": "DeterministicSchemaEvaluator"})
    events = live_event_bus.get_events(obs.session_id)
    det_evt = [e for e in events if e.event_type == LiveEventType.DETERMINISTIC_EVALUATION_COMPLETED][-1]
    assert det_evt.payload["evaluation_status"] == "PASSED"

def test_22_observer_diagnosis_and_remediation():
    """Verifies on_diagnosis and on_remediation."""
    run = TestRun(run_id="run_obs_diag", application_id="app_diag")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_diagnosis("diag_999", summary="HTTP 500 in backend controller")
    obs.on_remediation("rem_888", title="Add error boundary handling")

    events = live_event_bus.get_events(obs.session_id)
    d_evt = [e for e in events if e.event_type == LiveEventType.DIAGNOSIS_COMPLETED][-1]
    r_evt = [e for e in events if e.event_type == LiveEventType.REMEDIATION_PROPOSED][-1]
    assert d_evt.payload["diagnosis_id"] == "diag_999"
    assert r_evt.payload["task_id"] == "rem_888"

def test_23_observer_retest_event():
    """Verifies on_retest transition emission."""
    run = TestRun(run_id="run_obs_retest", application_id="app_retest")
    obs = LiveRunnerObserver.for_run(run)

    obs.on_retest("FIXED_FAILURE", comparisons=[{"dimension": "Prompt", "status": "CHANGED"}])
    events = live_event_bus.get_events(obs.session_id)
    ret_evt = [e for e in events if e.event_type == LiveEventType.RETEST_COMPLETED][-1]
    assert ret_evt.payload["transition"] == "FIXED_FAILURE"

def test_24_no_private_cot_exposed():
    """Verifies that private model reasoning / internal chain-of-thought is NOT in live events."""
    run = TestRun(run_id="run_obs_cot", application_id="app_cot")
    obs = LiveRunnerObserver.for_run(run)

    # Action started should only contain engineering structured descriptors
    obs.on_action_start("input", "Fill #topic-input with 'Science'", step_index=1, selector="#topic-input", value="Science")
    events = live_event_bus.get_events(obs.session_id)
    act_evt = [e for e in events if e.event_type == LiveEventType.ACTION_STARTED][-1]

    # Ensure no hidden private internal CoT fields are in the payload
    assert "private_reasoning" not in act_evt.payload
    assert "hidden_chain_of_thought" not in act_evt.payload
    assert "internal_prompt_weights" not in act_evt.payload

# ═══════════════════════════════════════════════════════════════════════
# 4. REST & SSE Endpoints
# ═══════════════════════════════════════════════════════════════════════

def test_25_api_list_sessions(client):
    """Verifies GET /api/v1/live/sessions returns registered sessions."""
    res = client.get("/api/v1/live/sessions")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)

def test_26_api_get_session_details(client, fresh_bus):
    """Verifies GET /api/v1/live/sessions/{session_id}."""
    sess = live_event_bus.create_session("run_api_detail", "target_01", "app_01")
    res = client.get(f"/api/v1/live/sessions/{sess.session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == sess.session_id
    assert data["run_id"] == "run_api_detail"

def test_27_api_get_event_history(client):
    """Verifies GET /api/v1/live/sessions/{session_id}/events/history."""
    sess = live_event_bus.create_session("run_api_hist", "target_01", "app_01")
    live_event_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)

    res = client.get(f"/api/v1/live/sessions/{sess.session_id}/events/history")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert data[0]["event_type"] == "SESSION_CREATED"
    assert data[1]["event_type"] == "SESSION_STARTED"

def test_28_api_get_screenshot(client):
    """Verifies GET /api/v1/live/sessions/{session_id}/screenshot returns image/png."""
    sess = live_event_bus.create_session("run_api_sc", "target_01", "app_01")
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    live_event_bus.store_latest_screenshot(sess.session_id, dummy_png)

    res = client.get(f"/api/v1/live/sessions/{sess.session_id}/screenshot")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content == dummy_png

def test_29_api_cancel_session(client):
    """Verifies POST /api/v1/live/sessions/{session_id}/cancel cancels session."""
    sess = live_event_bus.create_session("run_api_cancel", "target_01", "app_01")
    live_event_bus.publish(sess.session_id, LiveEventType.SESSION_STARTED)

    res = client.post(f"/api/v1/live/sessions/{sess.session_id}/cancel")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CANCELLED"

def test_30_api_launch_live_run(client):
    """Verifies POST /api/v1/live/launch creates run and live session in 1 request."""
    payload = {
        "application_id": "real_question_generator_local",
        "test_mode": "EXPLORATORY_DOGFOODING",
        "runner_type": "PLAYWRIGHT",
        "natural_language_goal": "Live test launch",
        "max_agent_steps": 5,
    }
    res = client.post("/api/v1/live/launch", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"].startswith("sess_live_")
    assert data["application_id"] == "real_question_generator_local"
    assert data["total_steps"] == 5
