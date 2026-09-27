from typing import Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from backend.app.git.service import GitService
from backend.app.lifecycle.repository import get_lifecycle_repo
from backend.app.lifecycle.pr_service import PRService
from backend.app.lifecycle.review_service import AICodeReviewService
from backend.app.lifecycle.ci_service import CIService
from backend.app.lifecycle.release_service import ReleaseReadinessService
from backend.app.lifecycle.models import PRStatus, CIStatus

router = APIRouter()

# Shared lifecycle services
git_service = GitService()
lifecycle_repo = get_lifecycle_repo()
pr_service = PRService(repository=lifecycle_repo, git_service=git_service)
review_service = AICodeReviewService()
ci_service = CIService(repository=lifecycle_repo)
release_service = ReleaseReadinessService(repository=lifecycle_repo)


class CreatePRRequest(BaseModel):
    repository: str = Field(default="antigravity-engineering-lab")
    title: str = Field(..., description="Title of the pull request")
    source_branch: str = Field(..., description="Source feature branch")
    target_branch: str = Field(default="main", description="Target base branch")
    description: str = Field(default="", description="Pull request description")


class TriggerCIRequest(BaseModel):
    commit_sha: str | None = Field(default=None, description="Commit SHA to run CI against")
    workflow: str = Field(default="pytest_unit", description="Workflow to execute: pytest_unit, npm_build, simulated_pass, simulated_fail")


@router.get("/status")
def get_git_status() -> dict[str, Any]:
    """Returns current repository status, active branch, and working tree cleanliness."""
    status = git_service.get_status()
    return status.model_dump()


@router.get("/diff")
def get_git_diff(base_sha: str | None = None, head_sha: str | None = None) -> dict[str, Any]:
    """Returns git diff for working tree or between two commits."""
    diff = git_service.get_diff(base_sha=base_sha, head_sha=head_sha)
    return diff.model_dump()


@router.get("/commits")
def get_commits(limit: int = Query(default=10, ge=1, le=50)) -> list[dict[str, Any]]:
    """Returns recent commit history with parent commits and metadata."""
    commits = git_service.get_recent_commits(limit=limit)
    return [c.model_dump() for c in commits]


@router.get("/pull-requests")
def list_pull_requests(
    repository: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> list[dict[str, Any]]:
    """Lists tracked pull requests."""
    prs = lifecycle_repo.list_prs(repository=repository)
    return [pr.model_dump() for pr in prs[:limit]]


@router.post("/pull-requests")
def create_pull_request(payload: CreatePRRequest) -> dict[str, Any]:
    """Creates and tracks a new pull request."""
    pr = pr_service.create_pull_request(
        title=payload.title,
        source_branch=payload.source_branch,
        target_branch=payload.target_branch,
        description=payload.description,
    )
    return pr.model_dump()


@router.get("/pull-requests/{pr_id}")
def get_pull_request(pr_id: str) -> dict[str, Any]:
    """Returns details for a pull request including any reviews."""
    pr = lifecycle_repo.get_pr(pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail=f"Pull request '{pr_id}' not found.")
    reviews = lifecycle_repo.get_reviews_for_pr(pr_id)
    return {
        "pull_request": pr.model_dump(),
        "reviews": [r.model_dump() for r in reviews],
    }


@router.post("/pull-requests/{pr_id}/review")
def review_pull_request(pr_id: str) -> dict[str, Any]:
    """Executes AI static code review on the pull request diff."""
    pr = lifecycle_repo.get_pr(pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail=f"Pull request '{pr_id}' not found.")

    diff = git_service.get_diff(base_sha=pr.base_sha, head_sha=pr.head_sha)
    review = review_service.review_diff(pr_id=pr.id, commit_sha=pr.head_sha, diff=diff)

    # If critical findings, request changes
    has_critical = any(f.severity.value in ("CRITICAL", "HIGH") for f in review.findings)
    new_status = PRStatus.CHANGES_REQUESTED if has_critical else PRStatus.APPROVED
    pr_service.update_status(pr_id, new_status)

    return review.model_dump()


@router.get("/ci/{commit_sha}")
def get_ci_runs(commit_sha: str) -> list[dict[str, Any]]:
    """Returns CI run status for a given commit."""
    runs = lifecycle_repo.get_ci_runs_for_commit(commit_sha)
    return [r.model_dump() for r in runs]


@router.post("/ci/run")
def trigger_ci_run(payload: TriggerCIRequest) -> dict[str, Any]:
    """Executes a deterministic CI workflow check for a commit."""
    commit_sha = payload.commit_sha
    if not commit_sha:
        commit_sha = git_service.get_head_commit_sha()

    ci_run = ci_service.trigger_ci_run(commit_sha=commit_sha, workflow=payload.workflow)
    return ci_run.model_dump()


@router.get("/release-readiness/{commit_sha}")
def get_release_readiness(commit_sha: str, pr_id: str | None = None) -> dict[str, Any]:
    """
    Evaluates end-to-end release readiness across Code Review, CI, Lab Verification, and Evidence.
    Preserves epistemic abstentions (UNKNOWN, ABSTAINED, INSUFFICIENT_DATA).
    """
    readiness = release_service.evaluate_readiness(commit_sha=commit_sha, pr_id=pr_id)
    return readiness.model_dump()
