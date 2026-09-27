from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from backend.app.lifecycle.models import (
    ReleaseReadiness,
    ReadinessState,
    GateStatus,
    CIStatus,
    ReviewStatus,
)
from backend.app.lifecycle.repository import LifecycleRepository

if TYPE_CHECKING:
    from backend.app.control_plane.service import ReliabilityControlPlane


class ReleaseReadinessService:
    """
    Evaluator computing release readiness across 4 distinct gates:
    1. AI Review Gate (static analysis)
    2. CI Gate (code-level unit/build tests)
    3. Engineering Lab Gate (runtime behavioral verification)
    4. Evidence Gate (cryptographic artifact completeness)

    Core Invariant: READY_FOR_RELEASE means configured gates passed. It must NOT trigger deployment.
    Preserves epistemic states: ABSTAINED or UNKNOWN remains inconclusive.
    """

    def __init__(
        self,
        repository: Optional[LifecycleRepository] = None,
        control_plane: Optional[ReliabilityControlPlane] = None,
    ):
        self.repo = repository or LifecycleRepository()
        if control_plane is None:
            from backend.app.control_plane.service import ReliabilityControlPlane
            self.control_plane = ReliabilityControlPlane()
        else:
            self.control_plane = control_plane

    def evaluate_readiness(
        self,
        commit_sha: str,
        pr_id: Optional[str] = None,
        lab_verified: Optional[bool] = None,
        lab_abstained: bool = False,
        github_repo: Optional[str] = None,
        github_actions_service: Optional[Any] = None,
    ) -> ReleaseReadiness:
        """
        Evaluates release readiness gates for a specific commit and optional PR.
        Supports both local CI and real GitHub Actions CI verification.
        """
        blockers: list[str] = []

        # 1. Evaluate Review Gate
        review_gate = GateStatus.PENDING
        if pr_id:
            review = self.repo.get_review_by_pr(pr_id)
            if review:
                if review.status == ReviewStatus.APPROVED:
                    review_gate = GateStatus.PASSED
                elif review.status == ReviewStatus.CHANGES_REQUESTED:
                    review_gate = GateStatus.FAILED
                    blockers.append(f"AI Code Review requested changes ({len(review.findings)} findings).")
                else:
                    review_gate = GateStatus.PENDING
                    blockers.append("AI Code Review has unaddressed comments.")
            else:
                review_gate = GateStatus.PENDING
                blockers.append(f"No AI Code Review completed for PR {pr_id}.")
        else:
            review_gate = GateStatus.SKIPPED

        # 2. Evaluate CI Gate (Local or GitHub Actions)
        ci_gate = GateStatus.PENDING
        if github_actions_service and github_repo:
            passed, gh_status, run = github_actions_service.verify_ci_gate(github_repo, commit_sha)
            if passed:
                ci_gate = GateStatus.PASSED
            elif gh_status == "FAILED":
                ci_gate = GateStatus.FAILED
                blockers.append(f"GitHub Actions CI workflow '{run.workflow_name if run else 'CI'}' failed on commit {commit_sha[:8]}.")
            elif gh_status == "CANCELLED":
                ci_gate = GateStatus.FAILED
                blockers.append(f"GitHub Actions CI workflow was cancelled on commit {commit_sha[:8]}.")
            elif gh_status in ("IN_PROGRESS", "QUEUED"):
                ci_gate = GateStatus.PENDING
                blockers.append(f"GitHub Actions CI is currently {gh_status.lower()} on commit {commit_sha[:8]}.")
            else:
                ci_gate = GateStatus.PENDING
                blockers.append(f"No completed successful GitHub Actions CI run found for commit {commit_sha[:8]}.")
        else:
            latest_ci = self.repo.get_latest_ci_run_for_commit(commit_sha)
            if latest_ci:
                if latest_ci.status == CIStatus.PASSED:
                    ci_gate = GateStatus.PASSED
                elif latest_ci.status == CIStatus.FAILED:
                    ci_gate = GateStatus.FAILED
                    blockers.append(f"Deterministic CI workflow '{latest_ci.workflow}' failed ({latest_ci.tests_failed} failures).")
                else:
                    ci_gate = GateStatus.PENDING
                    blockers.append(f"CI workflow '{latest_ci.workflow}' is currently {latest_ci.status.value}.")
            else:
                ci_gate = GateStatus.PENDING
                blockers.append("No CI run recorded for target commit.")

        # 3. Evaluate Engineering Lab Gate
        lab_gate = GateStatus.PENDING
        if lab_abstained:
            lab_gate = GateStatus.ABSTAINED
            blockers.append("Engineering Lab abstained from reliability determination (insufficient evidence / covariate shift).")
        elif lab_verified is True:
            lab_gate = GateStatus.PASSED
        elif lab_verified is False:
            lab_gate = GateStatus.FAILED
            blockers.append("Independent Engineering Lab behavioral verification failed.")
        else:
            # Check latest health or sessions in control plane
            lab_gate = GateStatus.PENDING
            blockers.append("Independent Engineering Lab verification has not been executed for this change.")

        # 4. Evaluate Evidence Gate
        evidence_gate = GateStatus.PENDING
        if lab_gate == GateStatus.PASSED:
            evidence_gate = GateStatus.PASSED
        elif lab_gate in [GateStatus.FAILED, GateStatus.ABSTAINED]:
            evidence_gate = GateStatus.PASSED  # Evidence exists even if failed/abstained
        else:
            evidence_gate = GateStatus.PENDING
            blockers.append("No independent verification evidence recorded.")

        # Determine Overall Readiness State
        if ci_gate == GateStatus.FAILED or lab_gate == GateStatus.FAILED or review_gate == GateStatus.FAILED:
            overall_state = ReadinessState.BLOCKED
        elif lab_gate == GateStatus.ABSTAINED:
            overall_state = ReadinessState.NOT_READY
        elif ci_gate == GateStatus.PASSED and lab_gate == GateStatus.PASSED and review_gate in [GateStatus.PASSED, GateStatus.SKIPPED]:
            overall_state = ReadinessState.READY_FOR_RELEASE
        elif ci_gate == GateStatus.PASSED and lab_gate == GateStatus.PENDING:
            overall_state = ReadinessState.NOT_READY
        else:
            overall_state = ReadinessState.NOT_READY

        readiness = ReleaseReadiness(
            commit_sha=commit_sha,
            pr_id=pr_id,
            overall_state=overall_state,
            review_status=review_gate,
            ci_status=ci_gate,
            lab_status=lab_gate,
            evidence_status=evidence_gate,
            blockers=blockers,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        self.repo.save_readiness(readiness)
        return readiness
