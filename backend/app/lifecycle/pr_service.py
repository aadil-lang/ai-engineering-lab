import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.lifecycle.models import PullRequest, PRStatus
from backend.app.lifecycle.repository import LifecycleRepository
from backend.app.git.service import GitService


class PRService:
    """
    Service managing Pull Request models, branch references, and lifecycle state transitions.
    Enforces invariant: CI success does NOT imply Lab verification.
    """

    def __init__(
        self,
        repository: Optional[LifecycleRepository] = None,
        git_service: Optional[GitService] = None,
    ):
        self.repo = repository or LifecycleRepository()
        self.git = git_service or GitService()

    def create_pull_request(
        self,
        title: str,
        source_branch: str,
        target_branch: str = "main",
        description: str = "",
        pr_number: Optional[int] = None,
    ) -> PullRequest:
        """Creates a new Pull Request tracking a source branch against target branch."""
        now_iso = datetime.now(timezone.utc).isoformat()
        num = pr_number or (len(self.repo.list_prs()) + 1)
        pr_id = f"pr-{num:03d}"

        # Determine SHAs
        try:
            head_sha = self.git._run_git(["rev-parse", source_branch])
        except Exception:
            head_sha = self.git.get_head_commit_sha()

        try:
            base_sha = self.git._run_git(["rev-parse", target_branch])
        except Exception:
            base_sha = head_sha

        pr = PullRequest(
            id=pr_id,
            repository=self.git.repo_name,
            number=num,
            title=title,
            description=description,
            source_branch=source_branch,
            target_branch=target_branch,
            head_sha=head_sha,
            base_sha=base_sha,
            status=PRStatus.OPEN,
            created_at=now_iso,
            updated_at=now_iso,
        )
        self.repo.save_pr(pr)
        return pr

    def get_pr(self, pr_id: str) -> Optional[PullRequest]:
        return self.repo.get_pr(pr_id)

    def list_prs(self) -> list[PullRequest]:
        return self.repo.list_prs()

    def update_status(self, pr_id: str, new_status: PRStatus) -> PullRequest:
        pr = self.get_pr(pr_id)
        if not pr:
            raise ValueError(f"Pull request not found: {pr_id}")

        now_iso = datetime.now(timezone.utc).isoformat()
        pr.status = new_status
        pr.updated_at = now_iso

        if new_status == PRStatus.MERGED:
            pr.merged_at = now_iso
        elif new_status == PRStatus.CLOSED:
            pr.closed_at = now_iso

        self.repo.save_pr(pr)
        return pr

    def transition_on_ci_result(self, pr_id: str, ci_passed: bool) -> PullRequest:
        """Transitions PR based on deterministic CI test results."""
        if not ci_passed:
            return self.update_status(pr_id, PRStatus.CI_FAILED)
        # CI passing does NOT mean approved or ready to merge; it remains OPEN or progresses
        pr = self.get_pr(pr_id)
        if pr and pr.status == PRStatus.CI_FAILED:
            return self.update_status(pr_id, PRStatus.OPEN)
        return pr or self.get_pr(pr_id)

    def transition_on_lab_result(self, pr_id: str, lab_verified: bool) -> PullRequest:
        """Transitions PR based on independent Engineering Lab verification."""
        if not lab_verified:
            return self.update_status(pr_id, PRStatus.LAB_FAILED)
        pr = self.get_pr(pr_id)
        if pr and pr.status == PRStatus.LAB_FAILED:
            return self.update_status(pr_id, PRStatus.OPEN)
        return pr or self.get_pr(pr_id)
