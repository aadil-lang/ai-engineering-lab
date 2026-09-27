from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class GitHubState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class GitHubRunStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GitHubRunConclusion(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    NEUTRAL = "neutral"


class GitHubRepository(BaseModel):
    github_id: int = Field(..., description="External GitHub repository ID")
    owner: str = Field(..., description="Repository owner or organization")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name: owner/name")
    default_branch: str = Field(default="main", description="Default branch")
    is_private: bool = Field(default=False, description="Whether the repository is private")
    html_url: str = Field(..., description="Web URL to repository")
    description: Optional[str] = Field(default=None, description="Repository description")


class GitHubBranch(BaseModel):
    name: str = Field(..., description="Branch name")
    commit_sha: str = Field(..., description="HEAD commit SHA of the branch")
    is_protected: bool = Field(default=False, description="Branch protection active")


class GitHubCommit(BaseModel):
    commit_sha: str = Field(..., description="40-character commit SHA")
    parent_commit_shas: list[str] = Field(default_factory=list, description="Parent commit SHAs")
    author_name: str = Field(..., description="Commit author name")
    author_email: str = Field(..., description="Commit author email")
    timestamp: str = Field(..., description="ISO-8601 commit timestamp")
    message: str = Field(..., description="Commit message")
    tree_sha: Optional[str] = Field(default=None, description="Git tree SHA")


class GitHubPullRequestFile(BaseModel):
    sha: str = Field(..., description="Blob SHA of the file")
    filename: str = Field(..., description="File path relative to repository root")
    status: str = Field(..., description="Change status: added, modified, removed, renamed")
    additions: int = Field(default=0, description="Added lines count")
    deletions: int = Field(default=0, description="Deleted lines count")
    changes: int = Field(default=0, description="Total changes count")
    patch: Optional[str] = Field(default=None, description="Unified diff patch chunk")


class GitHubPullRequest(BaseModel):
    github_id: int = Field(..., description="External GitHub pull request ID")
    number: int = Field(..., description="Pull request number")
    title: str = Field(..., description="PR title")
    body: Optional[str] = Field(default="", description="PR markdown description")
    state: GitHubState = Field(default=GitHubState.OPEN, description="GitHub PR state")
    head_branch: str = Field(..., description="Source feature branch")
    base_branch: str = Field(..., description="Target base branch")
    head_sha: str = Field(..., description="Exact head commit SHA evaluated")
    base_sha: str = Field(..., description="Base commit SHA")
    author_login: str = Field(..., description="GitHub username of PR author")
    html_url: str = Field(..., description="Web URL to pull request")
    is_draft: bool = Field(default=False, description="Whether PR is a draft")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    updated_at: str = Field(..., description="ISO-8601 last update timestamp")
    merged_at: Optional[str] = Field(default=None, description="ISO-8601 merge timestamp")
    closed_at: Optional[str] = Field(default=None, description="ISO-8601 close timestamp")


class GitHubWorkflowRun(BaseModel):
    github_run_id: int = Field(..., description="External GitHub Actions workflow run ID")
    workflow_name: str = Field(..., description="Name of the workflow")
    head_sha: str = Field(..., description="Exact commit SHA triggered by this run")
    head_branch: str = Field(..., description="Branch associated with the run")
    status: GitHubRunStatus = Field(..., description="Workflow execution status")
    conclusion: Optional[GitHubRunConclusion] = Field(default=None, description="Final run conclusion")
    html_url: str = Field(..., description="Web URL to workflow run")
    started_at: str = Field(..., description="ISO-8601 execution start timestamp")
    completed_at: Optional[str] = Field(default=None, description="ISO-8601 execution completion timestamp")
    duration_ms: int = Field(default=0, description="Duration in milliseconds")
    jobs_summary: Optional[str] = Field(default=None, description="Summary of executed jobs")


class GitHubCheckRun(BaseModel):
    github_check_id: int = Field(..., description="External GitHub check run ID")
    name: str = Field(..., description="Check name")
    head_sha: str = Field(..., description="Commit SHA")
    status: str = Field(..., description="queued, in_progress, completed")
    conclusion: Optional[str] = Field(default=None, description="success, failure, etc.")
    started_at: str = Field(..., description="ISO-8601 start timestamp")
    completed_at: Optional[str] = Field(default=None, description="ISO-8601 completion timestamp")


class GitHubPRComment(BaseModel):
    github_comment_id: int = Field(..., description="External GitHub comment ID")
    pr_number: int = Field(..., description="Pull request number")
    body: str = Field(..., description="Comment markdown body")
    author_login: str = Field(..., description="Comment author username")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    updated_at: str = Field(..., description="ISO-8601 update timestamp")
    idempotency_key: Optional[str] = Field(default=None, description="Deterministic key preventing duplicates")


class SynchronizedPR(BaseModel):
    """
    Synchronized Pull Request bridging external GitHub PR with local Engineering Lab lifecycle.
    Preserves independent behavioral verification states.
    """
    repository: str = Field(..., description="Repository full name: owner/name")
    pull_request_number: int = Field(..., description="GitHub PR number")
    head_branch: str = Field(..., description="Source feature branch")
    base_branch: str = Field(..., description="Target base branch")
    head_commit_sha: str = Field(..., description="Exact head commit SHA")
    base_commit_sha: str = Field(..., description="Base commit SHA")
    github_state: str = Field(..., description="GitHub native state: open, closed")
    local_lifecycle_state: str = Field(
        default="OPEN",
        description="Engineering Lab lifecycle state: OPEN, CHANGES_REQUESTED, APPROVED, CI_FAILED, LAB_FAILED, READY_FOR_HUMAN_REVIEW, READY_FOR_RELEASE, BLOCKED"
    )
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    updated_at: str = Field(..., description="ISO-8601 update timestamp")
    last_verified_commit_sha: Optional[str] = Field(default=None, description="Commit SHA verified by Engineering Lab")
    ci_verified_commit_sha: Optional[str] = Field(default=None, description="Commit SHA verified by GitHub Actions")
