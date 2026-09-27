"""
Comprehensive unit tests for Slice 7.5 — Git / PR / CI Lifecycle Services and Canonical Tools.
"""

import pytest
from pathlib import Path

from backend.app.git.service import GitService
from backend.app.git.models import GitFileStatus
from backend.app.lifecycle.models import (
    PRStatus,
    ReviewStatus,
    CIStatus,
    ReadinessState,
    GateStatus,
    FindingSeverity,
    EpistemicStatus,
)
from backend.app.lifecycle.repository import LifecycleRepository
from backend.app.lifecycle.pr_service import PRService
from backend.app.lifecycle.review_service import AICodeReviewService
from backend.app.lifecycle.ci_service import CIService
from backend.app.lifecycle.release_service import ReleaseReadinessService
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext


def test_git_service_status_and_commit():
    """Verify GitService reads active branch, clean/dirty state, and commit details."""
    git = GitService()
    assert git.is_git_repository() is True

    status = git.get_status()
    assert status.branch == "main"
    assert len(status.commit_sha) == 40
    assert status.repository is not None

    commit = git.get_commit(status.commit_sha)
    assert commit.commit_sha == status.commit_sha
    assert commit.author == "AI Engineering Lab"
    assert len(commit.message) > 0


def test_git_service_diff():
    """Verify GitService generates structured diffs with additions and deletions."""
    git = GitService()
    diff = git.get_diff()
    assert diff.repository is not None
    assert isinstance(diff.files, list)


def test_pr_lifecycle_transitions():
    """Verify PR creation and state transitions (CI failure, Lab failure)."""
    repo = LifecycleRepository(db_path=":memory:")
    git = GitService()
    pr_service = PRService(repository=repo, git_service=git)

    pr = pr_service.create_pull_request(
        title="Test Feature PR",
        source_branch="feature/test-1",
        target_branch="main",
        description="Testing PR state transitions",
    )
    assert pr.id.startswith("pr-")
    assert pr.status == PRStatus.OPEN

    # 1. CI failure transitions PR to CI_FAILED
    pr_after_ci_fail = pr_service.transition_on_ci_result(pr.id, ci_passed=False)
    assert pr_after_ci_fail.status == PRStatus.CI_FAILED

    # 2. CI passing resets to OPEN
    pr_after_ci_pass = pr_service.transition_on_ci_result(pr.id, ci_passed=True)
    assert pr_after_ci_pass.status == PRStatus.OPEN

    # 3. Lab failure transitions PR to LAB_FAILED
    pr_after_lab_fail = pr_service.transition_on_lab_result(pr.id, lab_verified=False)
    assert pr_after_lab_fail.status == PRStatus.LAB_FAILED


def test_ai_code_review_epistemic_distinctions():
    """Verify AI Code Review operates on diff and separates OBSERVED, INFERRED, and HYPOTHESIS findings."""
    review_service = AICodeReviewService()
    from backend.app.git.models import GitDiff, GitFileDiff

    sample_patch = (
        "diff --git a/test.py b/test.py\n"
        "--- a/test.py\n"
        "+++ b/test.py\n"
        "@@ -1,3 +1,7 @@\n"
        "+api_key = 'sk-1234567890abcdef12345678'\n"
        "+except:\n"
        "+    pass\n"
        "+global counter\n"
        "+# TODO: finalize implementation\n"
    )

    diff = GitDiff(
        repository="test_repo",
        base_sha="1111111111111111111111111111111111111111",
        head_sha="2222222222222222222222222222222222222222",
        files=[
            GitFileDiff(
                path="test.py",
                status=GitFileStatus.MODIFIED,
                additions=5,
                deletions=0,
                patch=sample_patch,
            )
        ],
        total_additions=5,
        total_deletions=0,
    )

    review = review_service.review_diff(pr_id="pr-999", commit_sha=diff.head_sha, diff=diff)

    assert review.status == ReviewStatus.CHANGES_REQUESTED
    assert len(review.findings) >= 4

    epistemic_statuses = {f.epistemic_status for f in review.findings}
    assert EpistemicStatus.OBSERVED in epistemic_statuses
    assert EpistemicStatus.INFERRED in epistemic_statuses
    assert EpistemicStatus.HYPOTHESIS in epistemic_statuses

    # Security finding is OBSERVED
    sec_finding = next(f for f in review.findings if f.category.value == "SECURITY")
    assert sec_finding.epistemic_status == EpistemicStatus.OBSERVED
    assert sec_finding.severity == FindingSeverity.CRITICAL

    # Bare except is INFERRED
    bug_finding = next(f for f in review.findings if f.category.value == "BUG")
    assert bug_finding.epistemic_status == EpistemicStatus.INFERRED

    # Concurrency hazard is HYPOTHESIS
    risk_finding = next(f for f in review.findings if f.category.value == "REGRESSION_RISK")
    assert risk_finding.epistemic_status == EpistemicStatus.HYPOTHESIS


def test_ci_service_deterministic_execution():
    """Verify deterministic CI workflows pass or fail without LLM override."""
    ci = CIService()

    # Simulated pass
    pass_run = ci.trigger_ci_run(commit_sha="46d15e9e", workflow="simulated_pass")
    assert pass_run.status == CIStatus.PASSED
    assert pass_run.tests_failed == 0
    assert pass_run.tests_passed == 10

    # Simulated fail
    fail_run = ci.trigger_ci_run(commit_sha="46d15e9e", workflow="simulated_fail")
    assert fail_run.status == CIStatus.FAILED
    assert fail_run.tests_failed == 2


def test_release_readiness_gates_and_abstention():
    """Verify release readiness evaluator rules, blockers, and epistemic abstention preservation."""
    repo = LifecycleRepository(db_path=":memory:")
    release_service = ReleaseReadinessService(repository=repo)
    commit = "46d15e9e11112222333344445555666677778888"

    # Scenario 1: No CI or Lab executed -> NOT_READY
    r1 = release_service.evaluate_readiness(commit_sha=commit)
    assert r1.overall_state == ReadinessState.NOT_READY
    assert len(r1.blockers) > 0

    # Scenario 2: CI failed -> BLOCKED
    from backend.app.lifecycle.models import CIRun
    repo.save_ci_run(
        CIRun(
            id="ci-test-1",
            commit_sha=commit,
            workflow="pytest_unit",
            status=CIStatus.FAILED,
            started_at="2026-09-27T00:00:00Z",
            tests_failed=1,
        )
    )
    r2 = release_service.evaluate_readiness(commit_sha=commit)
    assert r2.overall_state == ReadinessState.BLOCKED
    assert r2.ci_status == GateStatus.FAILED
    assert any("failed" in b.lower() for b in r2.blockers)

    # Scenario 3: CI passed, but Lab abstained -> NOT_READY (epistemic state preserved, NOT pass)
    repo.save_ci_run(
        CIRun(
            id="ci-test-2",
            commit_sha=commit,
            workflow="pytest_unit",
            status=CIStatus.PASSED,
            started_at="2026-09-27T00:01:00Z",
            tests_passed=10,
        )
    )
    r3 = release_service.evaluate_readiness(commit_sha=commit, lab_abstained=True)
    assert r3.overall_state == ReadinessState.NOT_READY
    assert r3.lab_status == GateStatus.ABSTAINED
    assert any("abstained" in b.lower() for b in r3.blockers)

    # Scenario 4: CI passed, Lab verified -> READY_FOR_RELEASE
    r4 = release_service.evaluate_readiness(commit_sha=commit, lab_verified=True)
    assert r4.overall_state == ReadinessState.READY_FOR_RELEASE
    assert r4.ci_status == GateStatus.PASSED
    assert r4.lab_status == GateStatus.PASSED
    assert len(r4.blockers) == 0


def test_control_plane_lifecycle_tools_invocations():
    """Verify all 6 canonical lifecycle tools can be invoked via the Control Plane registry."""
    cp = ReliabilityControlPlane(enable_lifecycle_tools=True)
    ctx = ToolInvocationContext(request_id="test-ctx-1", client_id="test-cli", actor_role="agent", transport="mcp")

    # 1. get_repository_status
    req_status = cp.registry.validate_request("get_repository_status", {})
    env_status = cp.registry.invoke("get_repository_status", req_status, ctx)
    assert env_status.success is True
    assert env_status.data.status.branch == "main"

    # 2. get_commit
    req_commit = cp.registry.validate_request("get_commit", {"commit_sha": "HEAD"})
    env_commit = cp.registry.invoke("get_commit", req_commit, ctx)
    assert env_commit.success is True
    assert env_commit.data.commit.author == "AI Engineering Lab"

    # 3. get_git_diff
    req_diff = cp.registry.validate_request("get_git_diff", {})
    env_diff = cp.registry.invoke("get_git_diff", req_diff, ctx)
    assert env_diff.success is True

    # 4. get_ci_status
    req_ci = cp.registry.validate_request("get_ci_status", {"commit_sha": "HEAD"})
    env_ci = cp.registry.invoke("get_ci_status", req_ci, ctx)
    assert env_ci.success is True

    # 5. get_pull_request (non-existent should return null PR cleanly)
    req_pr = cp.registry.validate_request("get_pull_request", {"pr_id": "pr-nonexistent"})
    env_pr = cp.registry.invoke("get_pull_request", req_pr, ctx)
    assert env_pr.success is True
    assert env_pr.data.pull_request is None

    # 6. get_release_readiness
    req_ready = cp.registry.validate_request("get_release_readiness", {"commit_sha": "HEAD"})
    env_ready = cp.registry.invoke("get_release_readiness", req_ready, ctx)
    assert env_ready.success is True
    assert env_ready.data.readiness.overall_state in [ReadinessState.NOT_READY, ReadinessState.BLOCKED, ReadinessState.READY_FOR_RELEASE]
