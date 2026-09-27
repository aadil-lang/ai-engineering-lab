"""
Integration test for Slice 7.5 — Controlled Failure and Remediation Lifecycle Loop.
Demonstrates:
Code change → CI/Lab failure → Evidence → Diagnosis → Fix → New commit → CI → Independent Lab verification → Release readiness.
Proves that an agent's claim alone is never sufficient; a new independent Lab execution must verify the change.
"""

import uuid
import pytest
from backend.app.git.service import GitService
from backend.app.lifecycle.models import (
    PRStatus,
    CIStatus,
    ReadinessState,
    GateStatus,
)
from backend.app.lifecycle.repository import LifecycleRepository
from backend.app.lifecycle.pr_service import PRService
from backend.app.lifecycle.review_service import AICodeReviewService
from backend.app.lifecycle.ci_service import CIService
from backend.app.lifecycle.release_service import ReleaseReadinessService
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext


def test_controlled_lifecycle_failure_and_remediation_loop():
    """
    Simulates a complete real-world engineering lifecycle:
    1. Feature implementation introducing a defect.
    2. CI and Lab behavioral verification detect failure.
    3. Failure forensic telemetry & epistemic diagnosis generated.
    4. Code fixed and committed with new commit SHA.
    5. CI passes on the new commit.
    6. Independent Engineering Lab re-verification verifies behavior.
    7. Release readiness gate transitions from BLOCKED to READY_FOR_RELEASE.
    """
    repo = LifecycleRepository(db_path=":memory:")
    git = GitService()
    cp = ReliabilityControlPlane(enable_lifecycle_tools=True)
    ctx = ToolInvocationContext(request_id="loop-ctx-1", client_id="test-agent", actor_role="agent", transport="mcp")

    pr_service = PRService(repository=repo, git_service=git)
    review_service = AICodeReviewService(repository=repo)
    ci_service = CIService(repository=repo)
    release_service = ReleaseReadinessService(repository=repo, control_plane=cp)

    # -------------------------------------------------------------------------
    # STEP 1: Code change & PR creation (initial commit with defect)
    # -------------------------------------------------------------------------
    bad_commit_sha = "c0ffee1111222233334444555566667777888899"
    pr = pr_service.create_pull_request(
        title="feat: add checkout discount validation",
        source_branch="feature/discount-code",
        target_branch="main",
        description="Support promotional discount coupons",
        pr_number=101,
    )
    assert pr.id == "pr-101"
    assert pr.status == PRStatus.OPEN

    # -------------------------------------------------------------------------
    # STEP 2: CI & Lab verification fail on bad commit
    # -------------------------------------------------------------------------
    # Trigger CI workflow
    ci_run_1 = ci_service.trigger_ci_run(commit_sha=bad_commit_sha, workflow="simulated_fail")
    assert ci_run_1.status == CIStatus.FAILED
    assert ci_run_1.tests_failed == 2

    # Update PR status on CI failure
    pr = pr_service.transition_on_ci_result(pr.id, ci_passed=False)
    assert pr.status == PRStatus.CI_FAILED

    # Independent Lab verification also fails
    pr = pr_service.transition_on_lab_result(pr.id, lab_verified=False)
    assert pr.status == PRStatus.LAB_FAILED

    # Check Release Readiness -> MUST BE BLOCKED
    r_initial = release_service.evaluate_readiness(
        commit_sha=bad_commit_sha,
        pr_id=pr.id,
        lab_verified=False,
    )
    assert r_initial.overall_state == ReadinessState.BLOCKED
    assert r_initial.ci_status == GateStatus.FAILED
    assert r_initial.lab_status == GateStatus.FAILED
    assert len(r_initial.blockers) >= 2

    # -------------------------------------------------------------------------
    # STEP 3: Evidence retrieval & epistemic diagnosis
    # -------------------------------------------------------------------------
    # Invoke list_failures to locate recent failures
    list_req = cp.registry.validate_request("list_failures", {"application_id": "app_inventory"})
    list_env = cp.registry.invoke("list_failures", list_req, ctx)
    assert list_env.success is True
    assert len(list_env.data.failures) > 0
    target_fail_id = list_env.data.failures[0].failure_id

    # Invoke get_failure via control plane
    fail_req = cp.registry.validate_request("get_failure", {"failure_id": target_fail_id})
    fail_env = cp.registry.invoke("get_failure", fail_req, ctx)
    assert fail_env.success is True

    # Invoke diagnose_failure
    diag_req = cp.registry.validate_request("diagnose_failure", {"failure_id": target_fail_id})
    diag_env = cp.registry.invoke("diagnose_failure", diag_req, ctx)
    assert diag_env.success is True
    assert len(diag_env.data.probable_root_causes) > 0

    # -------------------------------------------------------------------------
    # STEP 4: Agent claim without independent re-test is INSUFFICIENT
    # -------------------------------------------------------------------------
    # If agent simply claims it is fixed without triggering a new Lab run:
    r_claimed = release_service.evaluate_readiness(
        commit_sha=bad_commit_sha,
        pr_id=pr.id,
        lab_verified=None,  # Not verified yet
    )
    assert r_claimed.overall_state != ReadinessState.READY_FOR_RELEASE
    assert any("not been executed" in b.lower() or "failed" in b.lower() for b in r_claimed.blockers)

    # -------------------------------------------------------------------------
    # STEP 5: Fix applied & committed (new commit SHA)
    # -------------------------------------------------------------------------
    fixed_commit_sha = "d00d1e22223333444455556666777788889999aa"
    pr.head_sha = fixed_commit_sha
    repo.save_pr(pr)

    # -------------------------------------------------------------------------
    # STEP 6: CI executed on fixed commit -> PASSED
    # -------------------------------------------------------------------------
    ci_run_2 = ci_service.trigger_ci_run(commit_sha=fixed_commit_sha, workflow="simulated_pass")
    assert ci_run_2.status == CIStatus.PASSED
    assert ci_run_2.tests_failed == 0

    pr = pr_service.transition_on_ci_result(pr.id, ci_passed=True)

    # -------------------------------------------------------------------------
    # STEP 7: Independent Engineering Lab re-verification
    # -------------------------------------------------------------------------
    lab_session_req = cp.registry.validate_request(
        "start_test_session",
        {
            "application_id": "app_inventory",
            "scope": "SMOKE",
            "idempotency_key": f"verify-remediation-{uuid.uuid4().hex[:6]}",
        }
    )
    lab_session_env = cp.registry.invoke("start_test_session", lab_session_req, ctx)
    assert lab_session_env.success is True
    assert lab_session_env.data.status in ["ACTIVE", "SESSION_CREATED", "COMPLETED"]

    pr = pr_service.transition_on_lab_result(pr.id, lab_verified=True)

    # AI Code Review passes on clean diff
    from backend.app.git.models import GitDiff, GitFileDiff, GitFileStatus
    clean_diff = GitDiff(
        repository="test_repo",
        base_sha=bad_commit_sha,
        head_sha=fixed_commit_sha,
        files=[
            GitFileDiff(
                path="checkout.py",
                status=GitFileStatus.MODIFIED,
                additions=6,
                deletions=2,
                patch="@@ -10,2 +10,6 @@\n+if discount_rate < 0:\n+    raise ValueError('Negative discount')\n",
            )
        ],
        total_additions=6,
        total_deletions=2,
    )
    review_service.review_diff(pr_id=pr.id, commit_sha=fixed_commit_sha, diff=clean_diff)

    # -------------------------------------------------------------------------
    # STEP 8: Release Readiness re-evaluated -> READY_FOR_RELEASE
    # -------------------------------------------------------------------------
    r_final = release_service.evaluate_readiness(
        commit_sha=fixed_commit_sha,
        pr_id=pr.id,
        lab_verified=True,
    )
    assert r_final.overall_state == ReadinessState.READY_FOR_RELEASE
    assert r_final.review_status == GateStatus.PASSED
    assert r_final.ci_status == GateStatus.PASSED
    assert r_final.lab_status == GateStatus.PASSED
    assert r_final.evidence_status == GateStatus.PASSED
    assert len(r_final.blockers) == 0
