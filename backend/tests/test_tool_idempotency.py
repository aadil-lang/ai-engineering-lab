import pytest
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.models.tools import StartTestSessionRequest, SessionMode
from backend.app.control_plane.context import ToolInvocationContext


def test_start_test_session_idempotency():
    cp = ReliabilityControlPlane()
    ctx = ToolInvocationContext.create_default()

    req = StartTestSessionRequest(
        application_id="app_inventory",
        mode=SessionMode.reliability,
        scope="full",
        max_duration_seconds=120,
        idempotency_key="idemp_key_unique_12345",
    )

    # First invocation: creates session
    resp1 = cp.start_test_session(req, ctx)
    assert resp1.application_id == "app_inventory"
    assert resp1.status == "ACTIVE"
    assert not resp1.is_idempotent_replay

    # Second invocation with same idempotency key: reuses session
    resp2 = cp.start_test_session(req, ctx)
    assert resp2.session_id == resp1.session_id
    assert resp2.is_idempotent_replay is True
    assert resp2.started_at == resp1.started_at
