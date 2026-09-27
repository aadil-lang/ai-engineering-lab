from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "capabilities" in data

def test_list_targets():
    response = client.get("/api/v1/targets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_list_test_cases():
    response = client.get("/api/v1/test-cases")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5 # 5 modes seeded

def test_create_and_get_test_run():
    # 1. Fetch available target
    targets_resp = client.get("/api/v1/targets")
    assert targets_resp.status_code == 200
    target_id = targets_resp.json()[0]["target_id"]

    # 2. Trigger run
    run_payload = {
        "application_id": target_id,
        "test_mode": "FUNCTIONAL_QA",
        "simulate_failure": False,
        "action_delay_ms": 0,
    }
    create_resp = client.post("/api/v1/runs", json=run_payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    assert run_data["status"] == "PASSED"
    assert len(run_data["actions"]) == 5
    run_id = run_data["run_id"]

    # 3. Retrieve run by id
    get_resp = client.get(f"/api/v1/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run_id"] == run_id

    # 4. Fetch evidence
    evidence_resp = client.get(f"/api/v1/runs/{run_id}/evidence")
    assert evidence_resp.status_code == 200
    evidence_items = evidence_resp.json()
    assert len(evidence_items) == 5

    # 5. Fetch single evidence detail
    first_evi_id = evidence_items[0]["evidence_id"]
    single_evi_resp = client.get(f"/api/v1/runs/{run_id}/evidence/{first_evi_id}")
    assert single_evi_resp.status_code == 200
    assert single_evi_resp.json()["evidence_id"] == first_evi_id

def test_create_failing_test_run():
    targets_resp = client.get("/api/v1/targets")
    target_id = targets_resp.json()[0]["target_id"]

    run_payload = {
        "application_id": target_id,
        "test_mode": "AI_LLM_EVALUATION",
        "simulate_failure": True,
        "action_delay_ms": 0,
    }
    create_resp = client.post("/api/v1/runs", json=run_payload)
    assert create_resp.status_code == 201
    run_data = create_resp.json()
    assert run_data["status"] == "FAILED"
    assert len(run_data["failure_ids"]) == 1

    run_id = run_data["run_id"]
    failures_resp = client.get(f"/api/v1/runs/{run_id}/failures")
    assert failures_resp.status_code == 200
    failures = failures_resp.json()
    assert len(failures) == 1
    assert failures[0]["category"] == "LLM_HALLUCINATION"

def test_evidence_artifact_endpoint():
    import tempfile
    from pathlib import Path
    temp_dir = tempfile.mkdtemp()
    html_file = Path(temp_dir) / "test_api_page.html"
    html_file.write_text("<!DOCTYPE html><html><head><title>Test API Page</title></head><body><h1>API Test</h1></body></html>", encoding="utf-8")

    targets_resp = client.get("/api/v1/targets")
    target_id = targets_resp.json()[0]["target_id"]

    run_payload = {
        "application_id": target_id,
        "test_mode": "FUNCTIONAL_QA",
        "runner_type": "PLAYWRIGHT",
        "target_url_override": f"file:///{html_file.as_posix()}",
        "simulate_failure": False,
        "action_delay_ms": 0,
    }
    create_resp = client.post("/api/v1/runs", json=run_payload)
    assert create_resp.status_code == 201
    run_id = create_resp.json()["run_id"]

    # Fetch evidence list
    evi_resp = client.get(f"/api/v1/runs/{run_id}/evidence")
    assert evi_resp.status_code == 200
    items = evi_resp.json()
    assert len(items) > 0

    # Test downloading artifact file
    screenshot_evi = next((e for e in items if e["evidence_type"] == "SCREENSHOT"), None)
    if screenshot_evi and screenshot_evi.get("artifact_path"):
        art_resp = client.get(f"/api/v1/runs/{run_id}/evidence/{screenshot_evi['evidence_id']}/artifact")
        assert art_resp.status_code == 200
        assert len(art_resp.content) > 500
