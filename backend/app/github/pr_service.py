from datetime import datetime, timezone
from typing import Optional

from backend.app.github.client import GitHubClient, redact_secrets
from backend.app.github.models import SynchronizedPR, GitHubPullRequest
from backend.app.github.repository import GitHubSyncRepository, get_github_sync_repo
from backend.app.github.errors import StaleCommitVerificationError, GitHubPRNotFoundError
from backend.app.git.models import GitDiff, GitFileDiff, GitFileStatus
from backend.app.lifecycle.review_service import AICodeReviewService
from backend.app.lifecycle.models import PRReview, FindingSeverity, ReviewStatus


class GitHubPRService:
    """
    Manages synchronization between real GitHub Pull Requests and the Engineering Lab lifecycle.
    Enforces strict commit identity and invalidates prior verification upon PR updates (new head SHA).
    """

    def __init__(
        self,
        client: Optional[GitHubClient] = None,
        repository: Optional[GitHubSyncRepository] = None,
        review_service: Optional[AICodeReviewService] = None,
    ):
        self.client = client or GitHubClient()
        self.repo = repository or get_github_sync_repo()
        self.review_service = review_service or AICodeReviewService()

    def sync_pull_request(self, repository: str, pr_number: int) -> SynchronizedPR:
        """
        Fetches current state from GitHub and synchronizes local lifecycle tracking.
        If head_commit_sha has changed since last sync, invalidates prior verification.
        """
        gh_pr: GitHubPullRequest = self.client.get_pull_request(repository, pr_number)
        existing = self.repo.get_synced_pr(repository, pr_number)

        now_iso = datetime.now(timezone.utc).isoformat()

        if existing:
            # Check if head SHA has changed (PR update / new commit pushed)
            if existing.head_commit_sha != gh_pr.head_sha:
                # Invalidate stale commit verification
                synced = SynchronizedPR(
                    repository=repository,
                    pull_request_number=pr_number,
                    head_branch=gh_pr.head_branch,
                    base_branch=gh_pr.base_branch,
                    head_commit_sha=gh_pr.head_sha,
                    base_commit_sha=gh_pr.base_sha,
                    github_state=gh_pr.state.value,
                    local_lifecycle_state="OPEN",  # Reset to OPEN
                    created_at=existing.created_at,
                    updated_at=now_iso,
                    last_verified_commit_sha=None,  # Reset prior verification
                    ci_verified_commit_sha=None,     # Reset prior CI verification
                )
            else:
                # Keep verified SHAs if commit didn't change
                synced = SynchronizedPR(
                    repository=repository,
                    pull_request_number=pr_number,
                    head_branch=gh_pr.head_branch,
                    base_branch=gh_pr.base_branch,
                    head_commit_sha=gh_pr.head_sha,
                    base_commit_sha=gh_pr.base_sha,
                    github_state=gh_pr.state.value,
                    local_lifecycle_state=existing.local_lifecycle_state,
                    created_at=existing.created_at,
                    updated_at=now_iso,
                    last_verified_commit_sha=existing.last_verified_commit_sha,
                    ci_verified_commit_sha=existing.ci_verified_commit_sha,
                )
        else:
            synced = SynchronizedPR(
                repository=repository,
                pull_request_number=pr_number,
                head_branch=gh_pr.head_branch,
                base_branch=gh_pr.base_branch,
                head_commit_sha=gh_pr.head_sha,
                base_commit_sha=gh_pr.base_sha,
                github_state=gh_pr.state.value,
                local_lifecycle_state="OPEN",
                created_at=gh_pr.created_at,
                updated_at=now_iso,
                last_verified_commit_sha=None,
                ci_verified_commit_sha=None,
            )

        self.repo.save_synced_pr(synced)
        return synced

    def review_pull_request(self, repository: str, pr_number: int) -> PRReview:
        """
        Retrieves real PR diff from GitHub, parses it, and executes static AI code review.
        Updates synchronized PR status accordingly.
        """
        synced = self.sync_pull_request(repository, pr_number)
        raw_diff = self.client.get_pull_request_diff(repository, pr_number)
        files = self.client.get_pull_request_files(repository, pr_number)

        # Convert to GitDiff model for review_service
        file_diffs = []
        for f in files:
            file_diffs.append(
                GitFileDiff(
                    path=f.filename,
                    status=GitFileStatus.ADDED if f.status == "added" else (
                        GitFileStatus.DELETED if f.status == "removed" else GitFileStatus.MODIFIED
                    ),
                    additions=f.additions,
                    deletions=f.deletions,
                    patch=f.patch,
                )
            )

        total_add = sum(f.additions for f in file_diffs)
        total_del = sum(f.deletions for f in file_diffs)

        git_diff = GitDiff(
            repository=repository,
            base_sha=synced.base_commit_sha,
            head_sha=synced.head_commit_sha,
            files=file_diffs,
            total_additions=total_add,
            total_deletions=total_del,
        )

        pr_id = f"gh-{synced.pull_request_number}"
        review = self.review_service.review_diff(
            pr_id=pr_id,
            commit_sha=synced.head_commit_sha,
            diff=git_diff,
        )

        # Update local lifecycle state based on review findings
        has_critical = any(f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH] for f in review.findings)
        synced.local_lifecycle_state = "CHANGES_REQUESTED" if has_critical else "APPROVED"
        synced.updated_at = datetime.now(timezone.utc).isoformat()
        self.repo.save_synced_pr(synced)

        return review

    def publish_lab_comment(
        self,
        repository: str,
        pr_number: int,
        commit_sha: str,
        lab_status: str,
        ci_status: str,
        evidence_ids: list[str],
        release_readiness_state: str,
    ) -> str:
        """
        Posts a deterministic, concise Engineering Lab verification status comment to GitHub.
        Enforces idempotency using (repo + pr_number + commit_sha + check_type).
        Validates commit_sha matches current PR head_commit_sha to prevent stale reporting.
        """
        synced = self.repo.get_synced_pr(repository, pr_number)
        if not synced:
            synced = self.sync_pull_request(repository, pr_number)

        if synced.head_commit_sha != commit_sha:
            raise StaleCommitVerificationError(
                f"Cannot publish verification for stale commit {commit_sha[:8]}; "
                f"PR #{pr_number} current HEAD is {synced.head_commit_sha[:8]}."
            )

        idempotency_key = f"{repository}#{pr_number}#{commit_sha[:8]}#engineering-lab-verif"

        evidence_list = "\n".join(f"- `{eid}`" for eid in evidence_ids) if evidence_ids else "- _None recorded_"

        body = (
            f"### Engineering Lab Verification Report\n\n"
            f"**Commit:** `{commit_sha[:10]}`\n"
            f"**CI Status:** `{ci_status}`\n"
            f"**Runtime Verification:** `{lab_status}`\n"
            f"**Release Readiness:** `{release_readiness_state}`\n\n"
            f"**Evidence Artifacts:**\n"
            f"{evidence_list}\n\n"
            f"> *Note: Engineering Lab provides independent runtime behavioral verification. Final merge decision remains human-controlled.*"
        )

        comment = self.client.create_pr_comment(
            repo=repository,
            pr_number=pr_number,
            body=body,
            idempotency_key=idempotency_key,
        )
        return comment.body
