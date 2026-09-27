import json
import hmac
import hashlib
from datetime import datetime, timezone
import pytest
import httpx

from backend.app.github.client import GitHubClient, redact_secrets
from backend.app.github.repository import GitHubSyncRepository
from backend.app.github.pr_service import GitHubPRService
from backend.app.github.actions_service import GitHubActionsService
from backend.app.github.webhook_service import GitHubWebhookService
from backend.app.github.models import (
    GitHubPullRequest,
    GitHubWorkflowRun,
    GitHubRunStatus,
    GitHubRunConclusion,
    SynchronizedPR,
)
from backend.app.github.errors import (
    GitHubAuthenticationError,
    GitHubRepositoryNotFoundError,
    GitHubPRNotFoundError,
    GitHubCommitNotFoundError,
    GitHubWebhookVerificationError,
    StaleCommitVerificationError,
    GitHubError,
)
from backend.app.lifecycle.release_service import ReleaseReadinessService
from backend.app.lifecycle.models import ReadinessState, GateStatus


class MockGitHubTransport(httpx.BaseTransport):
    """
    In-memory mock transport simulating GitHub REST API v3 responses
    for all 18 edge cases and failure modes.
    """

    def __init__(self):
        self.prs: dict[int, dict] = {}
        self.runs: list[dict] = []
        self.comments: dict[int, list[dict]] = {}
        self.diffs: dict[int, str] = {}
        self.files: dict[int, list[dict]] = {}
        self.should_fail_auth = False
        self.should_fail_unavailable = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        path = request.url.path

        if self.should_fail_unavailable:
            return httpx.Response(503, text="Service Unavailable")

        if self.should_fail_auth:
            return httpx.Response(401, json={"message": "Bad credentials - token invalid"})

        # Repositories
        if path == "/repos/owner/valid-repo":
            return httpx.Response(200, json={
                "id": 12345,
                "owner": {"login": "owner"},
                "name": "valid-repo",
                "full_name": "owner/valid-repo",
                "default_branch": "main",
                "private": True,
                "html_url": "https://github.com/owner/valid-repo",
            })
        elif path == "/repos/owner/nonexistent-repo":
            return httpx.Response(404, json={"message": "Not Found"})

        # Pull Requests
        if path == "/repos/owner/valid-repo/pulls":
            if request.method == "GET":
                return httpx.Response(200, json=list(self.prs.values()))

        if path.startswith("/repos/owner/valid-repo/pulls/"):
            parts = path.split("/")
            pr_num = int(parts[5])

            if len(parts) == 6:  # /repos/owner/valid-repo/pulls/{num}
                if pr_num not in self.prs:
                    return httpx.Response(404, json={"message": f"Pull request #{pr_num} not found"})
                if "diff" in request.headers.get("accept", ""):
                    return httpx.Response(200, text=self.diffs.get(pr_num, ""))
                return httpx.Response(200, json=self.prs[pr_num])

            elif len(parts) == 7 and parts[6] == "files":
                return httpx.Response(200, json=self.files.get(pr_num, []))

        # Workflow Runs
        if path == "/repos/owner/valid-repo/actions/runs":
            head_sha = request.url.params.get("head_sha")
            matched = self.runs
            if head_sha:
                matched = [r for r in self.runs if r["head_sha"] == head_sha]
            return httpx.Response(200, json={"workflow_runs": matched})

        # Comments
        if path.startswith("/repos/owner/valid-repo/issues/"):
            pr_num = int(path.split("/")[5])
            if request.method == "GET":
                return httpx.Response(200, json=self.comments.get(pr_num, []))
            elif request.method == "POST":
                body = json.loads(request.content.decode("utf-8"))
                comment_id = len(self.comments.get(pr_num, [])) + 1
                c = {
                    "id": comment_id,
                    "body": body["body"],
                    "user": {"login": "antigravity-bot"},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                self.comments.setdefault(pr_num, []).append(c)
                return httpx.Response(201, json=c)

        # Commits
        if path.startswith("/repos/owner/valid-repo/commits/"):
            commit_sha = path.split("/")[-1]
            if commit_sha == "missing_sha":
                return httpx.Response(404, json={"message": "Commit not found"})
            return httpx.Response(200, json={
                "sha": commit_sha,
                "parents": [{"sha": "parent_sha_123"}],
                "commit": {
                    "author": {"name": "Engineer", "email": "dev@example.com", "date": datetime.now(timezone.utc).isoformat()},
                    "message": "Update code",
                    "tree": {"sha": "tree_sha_123"},
                }
            })

        return httpx.Response(404, json={"message": "Not Found"})


# =============================================================================
# 18 Explicit Failure & Security Tests
# =============================================================================

def test_case_01_invalid_credentials():
    transport = MockGitHubTransport()
    transport.should_fail_auth = True
    client = GitHubClient(token="ghp_invalid1234567890123456789012345678", transport=transport)

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        client.get_repository("owner/valid-repo")
    assert "authentication error" in str(exc_info.value).lower()


def test_case_02_repository_not_found():
    transport = MockGitHubTransport()
    client = GitHubClient(token="mock_token", transport=transport)

    with pytest.raises(GitHubRepositoryNotFoundError):
        client.get_repository("owner/nonexistent-repo")


def test_case_03_pr_not_found():
    transport = MockGitHubTransport()
    client = GitHubClient(token="mock_token", transport=transport)

    with pytest.raises(GitHubPRNotFoundError):
        client.get_pull_request("owner/valid-repo", 999)


def test_case_04_stale_pr_sha():
    transport = MockGitHubTransport()
    transport.prs[10] = {
        "id": 1001,
        "number": 10,
        "title": "PR Title",
        "state": "open",
        "head": {"ref": "feature", "sha": "new_commit_sha_999"},
        "base": {"ref": "main", "sha": "base_sha_000"},
        "user": {"login": "author"},
        "html_url": "https://github.com/owner/valid-repo/pull/10",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = GitHubClient(token="mock_token", transport=transport)
    repo = GitHubSyncRepository(db_path=":memory:")
    pr_service = GitHubPRService(client=client, repository=repo)

    # Sync with new_commit_sha_999
    pr_service.sync_pull_request("owner/valid-repo", 10)

    # Attempting to publish comments for old/stale SHA raises StaleCommitVerificationError
    with pytest.raises(StaleCommitVerificationError) as exc_info:
        pr_service.publish_lab_comment(
            repository="owner/valid-repo",
            pr_number=10,
            commit_sha="old_stale_commit_111",
            lab_status="PASSED",
            ci_status="PASSED",
            evidence_ids=["ev-1"],
            release_readiness_state="READY_FOR_HUMAN_REVIEW",
        )
    assert "stale commit" in str(exc_info.value).lower()


def test_case_05_ci_run_for_wrong_commit():
    transport = MockGitHubTransport()
    # Workflow run is for commit AAA, but query is for commit BBB
    transport.runs.append({
        "id": 501,
        "name": "CI",
        "head_sha": "commit_AAA",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/run/501",
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    })
    client = GitHubClient(token="mock_token", transport=transport)
    actions_service = GitHubActionsService(client=client, repository=GitHubSyncRepository(db_path=":memory:"))

    passed, gate_status, run = actions_service.verify_ci_gate("owner/valid-repo", "commit_BBB")
    assert passed is False
    assert gate_status == "CI_UNVERIFIED"


def test_case_06_ci_failure():
    transport = MockGitHubTransport()
    transport.runs.append({
        "id": 502,
        "name": "CI",
        "head_sha": "commit_CCC",
        "status": "completed",
        "conclusion": "failure",
        "html_url": "https://github.com/run/502",
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    })
    client = GitHubClient(token="mock_token", transport=transport)
    actions_service = GitHubActionsService(client=client, repository=GitHubSyncRepository(db_path=":memory:"))

    passed, gate_status, run = actions_service.verify_ci_gate("owner/valid-repo", "commit_CCC")
    assert passed is False
    assert gate_status == "FAILED"
    assert run.conclusion == GitHubRunConclusion.FAILURE


def test_case_07_ci_cancelled():
    transport = MockGitHubTransport()
    transport.runs.append({
        "id": 503,
        "name": "CI",
        "head_sha": "commit_DDD",
        "status": "completed",
        "conclusion": "cancelled",
        "html_url": "https://github.com/run/503",
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    })
    client = GitHubClient(token="mock_token", transport=transport)
    actions_service = GitHubActionsService(client=client, repository=GitHubSyncRepository(db_path=":memory:"))

    passed, gate_status, run = actions_service.verify_ci_gate("owner/valid-repo", "commit_DDD")
    assert passed is False
    assert gate_status == "CANCELLED"


def test_case_08_ci_timeout_or_in_progress():
    transport = MockGitHubTransport()
    transport.runs.append({
        "id": 504,
        "name": "CI",
        "head_sha": "commit_EEE",
        "status": "in_progress",
        "conclusion": None,
        "html_url": "https://github.com/run/504",
        "run_started_at": datetime.now(timezone.utc).isoformat(),
    })
    client = GitHubClient(token="mock_token", transport=transport)
    actions_service = GitHubActionsService(client=client, repository=GitHubSyncRepository(db_path=":memory:"))

    passed, gate_status, run = actions_service.verify_ci_gate("owner/valid-repo", "commit_EEE")
    assert passed is False
    assert gate_status == "IN_PROGRESS"


def test_case_09_lab_failure_blocks_release():
    release_service = ReleaseReadinessService()
    # lab_verified = False
    ready = release_service.evaluate_readiness(
        commit_sha="commit_FFF",
        lab_verified=False,
    )
    assert ready.overall_state == ReadinessState.BLOCKED
    assert ready.lab_status == GateStatus.FAILED
    assert any("behavioral verification failed" in b for b in ready.blockers)


def test_case_10_lab_unknown_preserves_not_ready():
    release_service = ReleaseReadinessService()
    # lab_verified is None (unknown/unexecuted)
    ready = release_service.evaluate_readiness(
        commit_sha="commit_GGG",
        lab_verified=None,
    )
    assert ready.overall_state == ReadinessState.NOT_READY
    assert ready.lab_status == GateStatus.PENDING
    assert ready.overall_state != ReadinessState.READY_FOR_RELEASE


def test_case_11_lab_abstained_never_becomes_passed():
    release_service = ReleaseReadinessService()
    ready = release_service.evaluate_readiness(
        commit_sha="commit_HHH",
        lab_abstained=True,
    )
    assert ready.lab_status == GateStatus.ABSTAINED
    assert ready.overall_state == ReadinessState.NOT_READY
    assert ready.overall_state != ReadinessState.READY_FOR_RELEASE


def test_case_12_webhook_signature_failure():
    webhook_service = GitHubWebhookService(webhook_secret="super-secret-key-123")
    payload = b'{"action": "opened"}'

    # Missing signature
    with pytest.raises(GitHubWebhookVerificationError):
        webhook_service.verify_signature(payload, None)

    # Invalid signature
    with pytest.raises(GitHubWebhookVerificationError):
        webhook_service.verify_signature(payload, "sha256=invalid_hex_string_123")


def test_case_13_duplicate_webhook_delivery_idempotency():
    repo = GitHubSyncRepository(db_path=":memory:")
    webhook_service = GitHubWebhookService(webhook_secret="test", repository=repo)

    delivery_id = "deliv_unique_abc_123"
    payload = {
        "action": "opened",
        "repository": {"full_name": "owner/valid-repo"},
        "pull_request": {
            "number": 12,
            "head": {"sha": "sha_12", "ref": "feat"},
            "base": {"sha": "sha_base", "ref": "main"},
            "state": "open",
        }
    }

    res1 = webhook_service.process_webhook_event("pull_request", delivery_id, payload)
    assert res1["status"] == "processed"

    # Second delivery with identical ID
    res2 = webhook_service.process_webhook_event("pull_request", delivery_id, payload)
    assert res2["status"] == "skipped"
    assert res2["reason"] == "duplicate_delivery"


def test_case_14_duplicate_pr_comment_prevention():
    transport = MockGitHubTransport()
    client = GitHubClient(token="mock_token", transport=transport)

    body = "Deterministic Report Content"
    key = "repo#pr1#sha1#check"

    c1 = client.create_pr_comment("owner/valid-repo", 1, body, idempotency_key=key)
    c2 = client.create_pr_comment("owner/valid-repo", 1, body, idempotency_key=key)

    # Returns the existing comment; list only has 1 comment
    assert c1.github_comment_id == c2.github_comment_id
    assert len(transport.comments[1]) == 1


def test_case_15_token_leakage_prevention():
    token = "ghp_Abcdef123456789012345678901234567890"
    raw_text = f"Authorization failed for header Bearer {token} with key ghp_Abcdef123456789012345678901234567890"
    scrubbed = redact_secrets(raw_text)

    assert token not in scrubbed
    assert "[REDACTED_GITHUB_TOKEN]" in scrubbed

    client = GitHubClient(token=token)
    assert token not in repr(client)
    assert token not in str(client)


def test_case_16_pr_updated_after_successful_verification():
    transport = MockGitHubTransport()
    transport.prs[5] = {
        "id": 5,
        "number": 5,
        "title": "Feature PR",
        "state": "open",
        "head": {"ref": "feature", "sha": "initial_sha_111"},
        "base": {"ref": "main", "sha": "base_sha_000"},
        "user": {"login": "author"},
        "html_url": "https://github.com/owner/valid-repo/pull/5",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = GitHubClient(token="mock_token", transport=transport)
    repo = GitHubSyncRepository(db_path=":memory:")
    pr_service = GitHubPRService(client=client, repository=repo)

    # Initial sync and simulate past verification
    synced = pr_service.sync_pull_request("owner/valid-repo", 5)
    synced.last_verified_commit_sha = "initial_sha_111"
    synced.ci_verified_commit_sha = "initial_sha_111"
    synced.local_lifecycle_state = "READY_FOR_RELEASE"
    repo.save_synced_pr(synced)

    # PR is updated with new head SHA
    transport.prs[5]["head"]["sha"] = "new_head_sha_222"

    # Re-sync
    updated_sync = pr_service.sync_pull_request("owner/valid-repo", 5)

    # Invariants verified: prior verification wiped out!
    assert updated_sync.head_commit_sha == "new_head_sha_222"
    assert updated_sync.last_verified_commit_sha is None
    assert updated_sync.ci_verified_commit_sha is None
    assert updated_sync.local_lifecycle_state == "OPEN"


def test_case_17_github_unavailable():
    transport = MockGitHubTransport()
    transport.should_fail_unavailable = True
    client = GitHubClient(token="mock_token", transport=transport)

    with pytest.raises(GitHubError) as exc_info:
        client.get_repository("owner/valid-repo")
    assert "503" in str(exc_info.value)


def test_case_18_insufficient_evidence_for_release_readiness():
    release_service = ReleaseReadinessService()
    ready = release_service.evaluate_readiness(
        commit_sha="commit_JJJ",
        lab_verified=None,
    )
    assert ready.overall_state == ReadinessState.NOT_READY
    assert ready.overall_state != ReadinessState.READY_FOR_RELEASE
    assert any("No independent verification evidence recorded" in b for b in ready.blockers)
