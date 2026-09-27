from typing import Optional, Any
from pydantic import BaseModel, Field

from backend.app.git.models import GitStatus, GitCommit, GitDiff
from backend.app.lifecycle.models import PullRequest, PRReview, CIRun, ReleaseReadiness


# 1. get_repository_status
class GetRepositoryStatusRequest(BaseModel):
    repository_path: Optional[str] = Field(default=None, description="Optional path to repository; defaults to workspace root")


class GetRepositoryStatusResponse(BaseModel):
    status: GitStatus


# 2. get_git_diff
class GetGitDiffRequest(BaseModel):
    base_sha: Optional[str] = Field(default=None, description="Base commit SHA (defaults to parent of head)")
    head_sha: Optional[str] = Field(default=None, description="Head commit SHA (defaults to HEAD)")


class GetGitDiffResponse(BaseModel):
    diff: GitDiff


# 3. get_commit
class GetCommitRequest(BaseModel):
    commit_sha: str = Field(default="HEAD", description="Commit SHA to inspect")


class GetCommitResponse(BaseModel):
    commit: GitCommit


# 4. get_pull_request
class GetPullRequestRequest(BaseModel):
    pr_id: str = Field(description="Pull request identifier (e.g. pr-001)")


class GetPullRequestResponse(BaseModel):
    pull_request: Optional[PullRequest] = None
    review: Optional[PRReview] = None


# 5. get_ci_status
class GetCIStatusRequest(BaseModel):
    commit_sha: str = Field(description="Commit SHA to query CI status for")


class GetCIStatusResponse(BaseModel):
    commit_sha: str
    latest_run: Optional[CIRun] = None


# 6. get_release_readiness
class GetReleaseReadinessRequest(BaseModel):
    commit_sha: str = Field(description="Commit SHA to evaluate release readiness for")
    pr_id: Optional[str] = Field(default=None, description="Optional PR identifier")


class GetReleaseReadinessResponse(BaseModel):
    readiness: ReleaseReadiness


# 7. get_github_repository
class GetGitHubRepositoryRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")


class GetGitHubRepositoryResponse(BaseModel):
    repository: Any


# 8. get_github_pull_request
class GetGitHubPullRequestRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")
    pr_number: int = Field(description="Pull request number")


class GetGitHubPullRequestResponse(BaseModel):
    pull_request: Any
    synchronized: Optional[Any] = None


# 9. get_github_pull_request_diff
class GetGitHubPullRequestDiffRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")
    pr_number: int = Field(description="Pull request number")


class GetGitHubPullRequestDiffResponse(BaseModel):
    diff_text: str
    files: list[Any] = Field(default_factory=list)


# 10. get_github_ci_status
class GetGitHubCIStatusRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")
    commit_sha: str = Field(description="Commit SHA to verify CI for")


class GetGitHubCIStatusResponse(BaseModel):
    commit_sha: str
    gate_status: str
    passed: bool
    latest_run: Optional[Any] = None


# 11. get_github_checks
class GetGitHubChecksRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")
    commit_sha: str = Field(description="Commit SHA to list checks for")


class GetGitHubChecksResponse(BaseModel):
    commit_sha: str
    checks: list[Any] = Field(default_factory=list)


# 12. get_github_pr_review
class GetGitHubPRReviewRequest(BaseModel):
    repository: str = Field(description="Full GitHub repository name: owner/repo")
    pr_number: int = Field(description="Pull request number to review")


class GetGitHubPRReviewResponse(BaseModel):
    review: PRReview
    synchronized: Any

