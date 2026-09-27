import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_list_capabilities(client):
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    caps = resp.json()
    assert len(caps) == 10
    tool_names = [c["name"] for c in caps]
    assert "inspect_application" in tool_names
    assert "start_test_session" in tool_names
    assert "get_application_health" in tool_names
    assert "get_prediction" in tool_names
    assert "get_uncertainty" in tool_names
    assert "list_failures" in tool_names
    assert "get_failure" in tool_names
    assert "diagnose_failure" in tool_names
    assert "get_evidence" in tool_names
    assert "get_reliability_summary" in tool_names


def test_api_get_mcp_schemas(client):
    resp = client.get("/api/tools/schemas/mcp")
    assert resp.status_code == 200
    schemas = resp.json()
    assert len(schemas) == 10
    for s in schemas:
        assert "name" in s
        assert "description" in s
        assert "inputSchema" in s
        assert "read_or_action" in s


def test_api_get_specific_tool_definition(client):
    resp = client.get("/api/tools/inspect_application")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "inspect_application"
    assert data["mode"] == "READ_ONLY"
    assert "input_schema" in data
    assert "output_schema" in data


def test_api_invoke_inspect_application(client):
    payload = {"application_id": "app_inventory"}
    resp = client.post("/api/tools/inspect_application/invoke", json=payload)
    assert resp.status_code == 200
    env = resp.json()
    assert env["success"] is True
    assert env["data"]["application_id"] == "app_inventory"
    assert env["metadata"]["tool_name"] == "inspect_application"
    assert env["metadata"]["provenance"]["snapshot_id"] == "eval_snap_slice_7_1"


def test_api_invoke_start_test_session_action(client):
    payload = {
        "application_id": "app_inventory",
        "mode": "reliability",
        "idempotency_key": "api_test_idemp_001",
    }
    resp1 = client.post("/api/tools/start_test_session/invoke", json=payload)
    assert resp1.status_code == 200
    env1 = resp1.json()
    assert env1["success"] is True
    assert env1["data"]["is_idempotent_replay"] is False
    sess_id = env1["data"]["session_id"]

    # Replay with same idempotency key
    resp2 = client.post("/api/tools/start_test_session/invoke", json=payload)
    assert resp2.status_code == 200
    env2 = resp2.json()
    assert env2["success"] is True
    assert env2["data"]["session_id"] == sess_id
    assert env2["data"]["is_idempotent_replay"] is True


def test_api_audit_recent(client):
    # Perform an invocation
    client.post("/api/tools/get_application_health/invoke", json={"application_id": "app_eda"})

    resp = client.get("/api/tools/audit/recent?limit=5")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) > 0
    assert "request_hash" in events[0]
    assert "response_hash" in events[0]
