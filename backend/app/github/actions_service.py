from typing import Optional, Tuple
from backend.app.github.client import GitHubClient
from backend.app.github.models import GitHubWorkflowRun, GitHubRunStatus, GitHubRunConclusion
from backend.app.github.repository import GitHubSyncRepository, get_github_sync_repo


class GitHubActionsService:
    """
    Service for integrating with GitHub Actions.
    Core Invariant: CI gates are deterministic.
    Verification requires:
      PR commit SHA == CI commit SHA
      AND CI completed
      AND CI conclusion == success
    An LLM cannot override a failed or missing CI check.
    """

    def __init__(
        self,
        client: Optional[GitHubClient] = None,
        repository: Optional[GitHubSyncRepository] = None,
    ):
        self.client = client or GitHubClient()
        self.repo = repository or get_github_sync_repo()

    def get_latest_run_for_commit(self, repository: str, commit_sha: str) -> Optional[GitHubWorkflowRun]:
        """Fetches the latest GitHub Actions workflow run for the exact commit SHA."""
        runs = self.client.list_workflow_runs(repository, commit_sha=commit_sha)
        if not runs:
            return None
        # Sort reverse chronologically
        latest = sorted(runs, key=lambda x: x.started_at, reverse=True)[0]
        self.repo.save_workflow_run(latest)
        return latest

    def verify_ci_gate(self, repository: str, commit_sha: str) -> Tuple[bool, str, Optional[GitHubWorkflowRun]]:
        """
        Evaluates deterministic CI verification gate for a specific commit SHA.
        Returns: (passed: bool, gate_status: str, run: Optional[GitHubWorkflowRun])
        Possible gate_status values:
          - 'PASSED'
          - 'FAILED'
          - 'IN_PROGRESS'
          - 'QUEUED'
          - 'CANCELLED'
          - 'CI_UNVERIFIED'
        """
        run = self.get_latest_run_for_commit(repository, commit_sha)
        if not run:
            return False, "CI_UNVERIFIED", None

        # Verify exact commit SHA match
        if run.head_sha != commit_sha:
            return False, "CI_UNVERIFIED", run

        if run.status == GitHubRunStatus.QUEUED:
            return False, "QUEUED", run
        elif run.status == GitHubRunStatus.IN_PROGRESS:
            return False, "IN_PROGRESS", run
        elif run.status == GitHubRunStatus.COMPLETED:
            if run.conclusion == GitHubRunConclusion.SUCCESS:
                return True, "PASSED", run
            elif run.conclusion == GitHubRunConclusion.CANCELLED:
                return False, "CANCELLED", run
            else:
                return False, "FAILED", run

        return False, "CI_UNVERIFIED", run
