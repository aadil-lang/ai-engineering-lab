import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_api_lifecycle_status(client):
    resp = client.get("/api/v1/lifecycle/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "branch" in data
    assert "is_clean" in data
    assert "commit_sha" in data


def test_api_lifecycle_diff(client):
    resp = client.get("/api/v1/lifecycle/diff")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data


def test_api_lifecycle_commits(client):
    resp = client.get("/api/v1/lifecycle/commits?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "commit_sha" in data[0]
        assert "message" in data[0]


def test_api_lifecycle_pull_requests_and_review(client):
    # Create PR
    pr_payload = {
        "repository": "antigravity-engineering-lab",
        "title": "API Lifecycle Feature Test",
        "source_branch": "main",
        "target_branch": "main",
    }
    resp = client.post("/api/v1/lifecycle/pull-requests", json=pr_payload)
    assert resp.status_code == 200
    pr_data = resp.json()
    pr_id = pr_data["id"]
    assert pr_data["title"] == "API Lifecycle Feature Test"

    # Get PR
    resp = client.get(f"/api/v1/lifecycle/pull-requests/{pr_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["pull_request"]["id"] == pr_id

    # Review PR
    resp = client.post(f"/api/v1/lifecycle/pull-requests/{pr_id}/review")
    assert resp.status_code == 200
    review_data = resp.json()
    assert review_data["pr_id"] == pr_id


def test_api_lifecycle_ci_and_release_readiness(client):
    status_resp = client.get("/api/v1/lifecycle/status")
    head_sha = status_resp.json()["commit_sha"]

    # Trigger CI
    ci_resp = client.post("/api/v1/lifecycle/ci/run", json={"commit_sha": head_sha, "workflow": "simulated_pass"})
    assert ci_resp.status_code == 200
    ci_data = ci_resp.json()
    assert ci_data["status"] == "PASSED"

    # Get CI runs
    runs_resp = client.get(f"/api/v1/lifecycle/ci/{head_sha}")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert any(r["commit_sha"] == head_sha for r in runs)

    # Evaluate Release Readiness
    readiness_resp = client.get(f"/api/v1/lifecycle/release-readiness/{head_sha}")
    assert readiness_resp.status_code == 200
    readiness = readiness_resp.json()
    assert readiness["commit_sha"] == head_sha
    assert "overall_state" in readiness
    assert "blockers" in readiness
