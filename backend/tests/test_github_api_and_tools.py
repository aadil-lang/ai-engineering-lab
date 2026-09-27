import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.github.client import GitHubClient
from backend.app.github.repository import GitHubSyncRepository
from backend.app.github.pr_service import GitHubPRService
from backend.app.github.actions_service import GitHubActionsService
from backend.tests.test_github_client_and_services import MockGitHubTransport


@pytest.fixture
def client():
    return TestClient(app)


def test_control_plane_github_tools_registration_and_invocation():
    transport = MockGitHubTransport()
    transport.prs[1] = {
        "id": 101,
        "number": 1,
        "title": "PR One",
        "body": "Body",
        "state": "open",
        "head": {"ref": "feature", "sha": "head_sha_123"},
        "base": {"ref": "main", "sha": "base_sha_000"},
        "user": {"login": "dev"},
        "html_url": "https://github.com/owner/valid-repo/pull/1",
        "created_at": "2026-09-27T08:00:00Z",
        "updated_at": "2026-09-27T08:00:00Z",
    }
    transport.diffs[1] = "diff --git a/a.py b/a.py\n+hello"
    transport.files[1] = [{"sha": "b1", "filename": "a.py", "status": "added", "additions": 1, "deletions": 0, "changes": 1, "patch": "+hello"}]
    transport.runs.append({
        "id": 77,
        "name": "CI",
        "head_sha": "head_sha_123",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/runs/77",
        "run_started_at": "2026-09-27T08:05:00Z",
    })

    gh_client = GitHubClient(token="mock_token", transport=transport)
    sync_repo = GitHubSyncRepository(db_path=":memory:")
    pr_service = GitHubPRService(client=gh_client, repository=sync_repo)
    actions_service = GitHubActionsService(client=gh_client, repository=sync_repo)

    # Control plane with github tools
    cp = ReliabilityControlPlane(enable_github_tools=True)
    cp.register_github_tools(
        github_client=gh_client,
        github_sync_repo=sync_repo,
        github_pr_service=pr_service,
        github_actions_service=actions_service,
    )

    ctx = ToolInvocationContext.create_default(actor="test-agent")

    # 1. get_github_repository
    res_repo = cp.registry.invoke(
        "get_github_repository",
        cp.registry.validate_request("get_github_repository", {"repository": "owner/valid-repo"}),
        ctx,
    )
    assert res_repo.success is True
    repo_val = res_repo.data.repository
    repo_name = repo_val["name"] if isinstance(repo_val, dict) else repo_val.name
    assert repo_name == "valid-repo"

    # 2. get_github_pull_request
    res_pr = cp.registry.invoke(
        "get_github_pull_request",
        cp.registry.validate_request("get_github_pull_request", {"repository": "owner/valid-repo", "pr_number": 1}),
        ctx,
    )
    assert res_pr.success is True
    pr_val = res_pr.data.pull_request
    pr_num = pr_val["number"] if isinstance(pr_val, dict) else pr_val.number
    assert pr_num == 1

    # 3. get_github_pull_request_diff
    res_diff = cp.registry.invoke(
        "get_github_pull_request_diff",
        cp.registry.validate_request("get_github_pull_request_diff", {"repository": "owner/valid-repo", "pr_number": 1}),
        ctx,
    )
    assert res_diff.success is True
    assert "diff" in res_diff.data.diff_text

    # 4. get_github_ci_status
    res_ci = cp.registry.invoke(
        "get_github_ci_status",
        cp.registry.validate_request("get_github_ci_status", {"repository": "owner/valid-repo", "commit_sha": "head_sha_123"}),
        ctx,
    )
    assert res_ci.success is True
    assert res_ci.data.passed is True
    assert res_ci.data.gate_status == "PASSED"

    # 5. get_github_pr_review
    res_rev = cp.registry.invoke(
        "get_github_pr_review",
        cp.registry.validate_request("get_github_pr_review", {"repository": "owner/valid-repo", "pr_number": 1}),
        ctx,
    )
    assert res_rev.success is True
    synced_val = res_rev.data.synchronized
    head_sha = synced_val["head_commit_sha"] if isinstance(synced_val, dict) else synced_val.head_commit_sha
    assert head_sha == "head_sha_123"


def test_api_github_webhooks(client):
    delivery_id = f"delivery_test_{uuid.uuid4().hex[:12]}"
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/valid-repo"},
        "pull_request": {
            "number": 88,
            "head": {"sha": "sha_88", "ref": "feat-88"},
            "base": {"sha": "base_sha", "ref": "main"},
            "state": "open",
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Send webhook
    resp = client.post(
        "/api/v1/github/webhooks",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": delivery_id,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["pr_number"] == 88

    # Duplicate delivery
    resp_dup = client.post(
        "/api/v1/github/webhooks",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": delivery_id,
        },
    )
    assert resp_dup.status_code == 200
    dup_data = resp_dup.json()
    assert dup_data["status"] == "skipped"
    assert dup_data["reason"] == "duplicate_delivery"
