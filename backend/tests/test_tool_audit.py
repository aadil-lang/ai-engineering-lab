import pytest
from backend.app.control_plane.audit import AuditLogger, AuditEvent


def test_audit_event_sha256_hashing():
    AuditLogger.clear()

    req = {"application_id": "app_eda", "token": "sensitive_password_123"}
    resp = {"status": "HEALTHY"}

    event = AuditLogger.record_invocation(
        request_id="req_test_001",
        tool_name="get_application_health",
        tool_version="1.0",
        application_id="app_eda",
        session_id="sess_001",
        actor="agent_v1",
        request_data=req,
        response_data=resp,
        result_status="SUCCESS",
        execution_time_ms=12.4,
    )

    assert event.request_id == "req_test_001"
    assert len(event.request_hash) == 64  # SHA-256 hex length
    assert len(event.response_hash) == 64
    assert event.result_status == "SUCCESS"

    # Verify no raw passwords exist in audit record
    record_json = event.model_dump_json()
    assert "sensitive_password_123" not in record_json


def test_audit_recent_and_session_queries():
    AuditLogger.clear()

    for i in range(5):
        AuditLogger.record_invocation(
            request_id=f"req_{i}",
            tool_name="inspect_application",
            tool_version="1.0",
            application_id="app_booking",
            session_id="sess_target" if i < 3 else "sess_other",
            actor="agent",
            request_data={"idx": i},
            response_data={"ok": True},
            result_status="SUCCESS",
            execution_time_ms=5.0,
        )

    recent = AuditLogger.get_recent_events(limit=10)
    assert len(recent) == 5

    session_events = AuditLogger.get_events_for_session("sess_target")
    assert len(session_events) == 3
