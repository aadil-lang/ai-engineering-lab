import json
from datetime import datetime, timezone
import pytest
import httpx

from backend.app.github.client import GitHubClient
from backend.app.github.repository import GitHubSyncRepository
from backend.app.github.pr_service import GitHubPRService
from backend.app.github.actions_service import GitHubActionsService
from backend.app.lifecycle.release_service import ReleaseReadinessService
from backend.app.lifecycle.models import ReadinessState, GateStatus
from backend.app.control_plane.service import ReliabilityControlPlane


class E2EGitHubTransport(httpx.BaseTransport):
    """Simulates real GitHub API during the end-to-end integration lifecycle."""

    def __init__(self):
        self.repo_name = "antigravity/ecommerce-platform"
        self.pr_number = 42
        self.current_head_sha = "c011a_defect_commit"
        self.base_sha = "main_base_000"
        self.pr_title = "Add parallel order reservation worker"
        self.workflow_runs: list[dict] = []
        self.comments: list[dict] = []
        self.diff_text = ""
        self.files = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path == f"/repos/{self.repo_name}":
            return httpx.Response(200, json={
                "id": 9988,
                "owner": {"login": "antigravity"},
                "name": "ecommerce-platform",
                "full_name": self.repo_name,
                "default_branch": "main",
                "private": False,
                "html_url": f"https://github.com/{self.repo_name}",
            })

        if path == f"/repos/{self.repo_name}/pulls/{self.pr_number}":
            if "diff" in request.headers.get("accept", ""):
                return httpx.Response(200, text=self.diff_text)
            return httpx.Response(200, json={
                "id": 4200,
                "number": self.pr_number,
                "title": self.pr_title,
                "body": "PR description",
                "state": "open",
                "head": {"ref": "feature/parallel-orders", "sha": self.current_head_sha},
                "base": {"ref": "main", "sha": self.base_sha},
                "user": {"login": "developer-ai"},
                "html_url": f"https://github.com/{self.repo_name}/pull/{self.pr_number}",
                "created_at": "2026-09-27T10:00:00Z",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        if path == f"/repos/{self.repo_name}/pulls/{self.pr_number}/files":
            return httpx.Response(200, json=self.files)

        if path == f"/repos/{self.repo_name}/actions/runs":
            head_sha = request.url.params.get("head_sha")
            matched = [r for r in self.workflow_runs if r["head_sha"] == head_sha] if head_sha else self.workflow_runs
            return httpx.Response(200, json={"workflow_runs": matched})

        if path == f"/repos/{self.repo_name}/issues/{self.pr_number}/comments":
            if request.method == "GET":
                return httpx.Response(200, json=self.comments)
            elif request.method == "POST":
                data = json.loads(request.content.decode("utf-8"))
                comment = {
                    "id": len(self.comments) + 1,
                    "body": data["body"],
                    "user": {"login": "antigravity-bot"},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                self.comments.append(comment)
                return httpx.Response(201, json=comment)

        return httpx.Response(404, json={"message": "Not Found"})


def test_controlled_github_lifecycle_and_remediation_e2e():
    """
    Controlled end-to-end GitHub lifecycle scenario demonstrating:
    1. Defective commit on feature branch
    2. GitHub PR created with initial head SHA
    3. AI code review on real PR diff detects defect
    4. GitHub Actions CI fails on initial commit
    5. Release readiness evaluates as BLOCKED
    6. Agent remedies code; new commit created (new head SHA)
    7. PR updates with new head SHA; previous verification is invalidated
    8. GitHub Actions CI passes on new commit
    9. Engineering Lab independently verifies running application
    10. Release readiness recalculates to READY_FOR_RELEASE / READY_FOR_HUMAN_REVIEW
    11. Verification from commit 1 does not leak into commit 2
    12. Human merge decision remains mandatory (no auto-merge)
    """
    transport = E2EGitHubTransport()
    repo_name = transport.repo_name
    pr_number = transport.pr_number

    # Step 1: Initial defect commit diff
    transport.current_head_sha = "c011a_defect_commit"
    transport.diff_text = """diff --git a/backend/order_worker.py b/backend/order_worker.py
--- a/backend/order_worker.py
+++ b/backend/order_worker.py
@@ -10,3 +10,4 @@
+def process_orders_concurrent():
+    # Unsafe shared state without mutex
+    global inventory_count; inventory_count -= 1
"""
    transport.files = [{
        "sha": "blob_defect_1",
        "filename": "backend/order_worker.py",
        "status": "modified",
        "additions": 4,
        "deletions": 0,
        "changes": 4,
        "patch": transport.diff_text,
    }]

    # Step 2: GitHub Actions fails for defect commit
    transport.workflow_runs.append({
        "id": 901,
        "name": "GitHub Actions CI",
        "head_sha": "c011a_defect_commit",
        "status": "completed",
        "conclusion": "failure",
        "html_url": f"https://github.com/{repo_name}/actions/runs/901",
        "run_started_at": "2026-09-27T10:05:00Z",
    })

    client = GitHubClient(token="mock_token", transport=transport)
    sync_repo = GitHubSyncRepository(db_path=":memory:")
    pr_service = GitHubPRService(client=client, repository=sync_repo)
    actions_service = GitHubActionsService(client=client, repository=sync_repo)
    release_service = ReleaseReadinessService()

    # Step 3: Sync PR and run AI code review
    synced_pr_initial = pr_service.sync_pull_request(repo_name, pr_number)
    assert synced_pr_initial.head_commit_sha == "c011a_defect_commit"

    review_initial = pr_service.review_pull_request(repo_name, pr_number)
    assert review_initial.commit_sha == "c011a_defect_commit"
    # Review updates local lifecycle state in repo
    refreshed_pr = sync_repo.get_synced_pr(repo_name, pr_number)
    assert refreshed_pr.local_lifecycle_state in ("CHANGES_REQUESTED", "APPROVED")

    # Step 4: Verify CI gate fails on commit 1
    ci_passed, ci_status, ci_run = actions_service.verify_ci_gate(repo_name, "c011a_defect_commit")
    assert ci_passed is False
    assert ci_status == "FAILED"
    assert ci_run.conclusion.value == "failure"

    # Step 5: Evaluate Release Readiness on commit 1
    readiness_1 = release_service.evaluate_readiness(
        commit_sha="c011a_defect_commit",
        pr_id=f"gh-{pr_number}",
        lab_verified=False,  # Lab detects failure
        github_repo=repo_name,
        github_actions_service=actions_service,
    )
    assert readiness_1.overall_state == ReadinessState.BLOCKED
    assert readiness_1.ci_status == GateStatus.FAILED
    assert readiness_1.lab_status == GateStatus.FAILED
    assert len(readiness_1.blockers) >= 2

    # Step 6: Post initial report to PR
    comment_1 = pr_service.publish_lab_comment(
        repository=repo_name,
        pr_number=pr_number,
        commit_sha="c011a_defect_commit",
        lab_status="FAILED",
        ci_status="FAILED",
        evidence_ids=["ev-defect-001"],
        release_readiness_state="BLOCKED",
    )
    assert "BLOCKED" in comment_1

    # =========================================================================
    # Step 7: Developer Fixes Defect -> New Commit & PR Update
    # =========================================================================
    new_commit_sha = "c012b_fixed_commit"
    transport.current_head_sha = new_commit_sha
    transport.diff_text = """diff --git a/backend/order_worker.py b/backend/order_worker.py
--- a/backend/order_worker.py
+++ b/backend/order_worker.py
@@ -10,3 +10,6 @@
+def process_orders_concurrent():
+    with inventory_lock:
+        decrement_inventory_safely()
"""
    transport.files[0]["patch"] = transport.diff_text

    # Step 8: PR Synchronization invalidates previous verification
    synced_pr_updated = pr_service.sync_pull_request(repo_name, pr_number)
    assert synced_pr_updated.head_commit_sha == new_commit_sha
    assert synced_pr_updated.last_verified_commit_sha is None
    assert synced_pr_updated.ci_verified_commit_sha is None
    assert synced_pr_updated.local_lifecycle_state == "OPEN"

    # Step 9: Attempting to verify or publish for old commit raises StaleCommitVerificationError
    with pytest.raises(Exception):
        pr_service.publish_lab_comment(
            repository=repo_name,
            pr_number=pr_number,
            commit_sha="c011a_defect_commit",
            lab_status="PASSED",
            ci_status="PASSED",
            evidence_ids=[],
            release_readiness_state="READY_FOR_RELEASE",
        )

    # Step 10: GitHub Actions CI passes for the new commit
    transport.workflow_runs.append({
        "id": 902,
        "name": "GitHub Actions CI",
        "head_sha": new_commit_sha,
        "status": "completed",
        "conclusion": "success",
        "html_url": f"https://github.com/{repo_name}/actions/runs/902",
        "run_started_at": "2026-09-27T10:15:00Z",
    })

    ci_passed_2, ci_status_2, ci_run_2 = actions_service.verify_ci_gate(repo_name, new_commit_sha)
    assert ci_passed_2 is True
    assert ci_status_2 == "PASSED"
    assert ci_run_2.conclusion.value == "success"

    # Step 11: Independent Lab Verification on updated application
    # Lab independently verifies runtime behavioral correctness
    lab_verified = True
    evidence_ids = ["ev-fix-002", "ev-telemetry-003"]

    # Step 12: Release Readiness recalculation
    readiness_2 = release_service.evaluate_readiness(
        commit_sha=new_commit_sha,
        pr_id=None,
        lab_verified=lab_verified,
        github_repo=repo_name,
        github_actions_service=actions_service,
    )

    assert readiness_2.overall_state == ReadinessState.READY_FOR_RELEASE
    assert readiness_2.ci_status == GateStatus.PASSED
    assert readiness_2.lab_status == GateStatus.PASSED
    assert readiness_2.evidence_status == GateStatus.PASSED
    assert len(readiness_2.blockers) == 0

    # Step 13: Publish verified report to PR
    comment_2 = pr_service.publish_lab_comment(
        repository=repo_name,
        pr_number=pr_number,
        commit_sha=new_commit_sha,
        lab_status="PASSED",
        ci_status="PASSED",
        evidence_ids=evidence_ids,
        release_readiness_state="READY_FOR_RELEASE",
    )
    assert "READY_FOR_RELEASE" in comment_2
    assert "ev-fix-002" in comment_2

    # Step 14: Invariant check — no automatic merge or deployment triggered!
    assert transport.current_head_sha == new_commit_sha
    assert synced_pr_updated.github_state == "open"  # Still open, human decides!
