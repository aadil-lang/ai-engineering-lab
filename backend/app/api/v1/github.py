import os
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, Header, Request, Body
from pydantic import BaseModel, Field

from backend.app.github.client import GitHubClient
from backend.app.github.repository import get_github_sync_repo
from backend.app.github.pr_service import GitHubPRService
from backend.app.github.actions_service import GitHubActionsService
from backend.app.github.webhook_service import GitHubWebhookService
from backend.app.github.errors import (
    GitHubError,
    GitHubAuthenticationError,
    GitHubRepositoryNotFoundError,
    GitHubPRNotFoundError,
    GitHubWebhookVerificationError,
    StaleCommitVerificationError,
)

router = APIRouter()

# Default services
github_client = GitHubClient()
github_repo = get_github_sync_repo()
pr_service = GitHubPRService(client=github_client, repository=github_repo)
actions_service = GitHubActionsService(client=github_client, repository=github_repo)
webhook_service = GitHubWebhookService(repository=github_repo)


class PublishCommentRequest(BaseModel):
    commit_sha: str = Field(..., description="Commit SHA being verified")
    lab_status: str = Field(..., description="Engineering Lab verification status")
    ci_status: str = Field(default="PASSED", description="GitHub Actions CI status")
    evidence_ids: list[str] = Field(default_factory=list, description="Chained evidence IDs")
    release_readiness_state: str = Field(default="READY_FOR_HUMAN_REVIEW", description="Readiness state")


@router.get("/repository")
def get_repository_metadata(
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab"))
) -> dict[str, Any]:
    """Retrieves authenticated metadata for the configured GitHub repository."""
    try:
        repo = github_client.get_repository(repository)
        return repo.model_dump()
    except GitHubAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GitHubRepositoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/pull-requests")
def list_pull_requests(
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
    state: str = Query(default="open"),
) -> list[dict[str, Any]]:
    """Lists pull requests from GitHub."""
    try:
        prs = github_client.list_pull_requests(repository, state=state)
        return [pr.model_dump() for pr in prs]
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/pull-requests/{number}")
def get_pull_request_detail(
    number: int,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> dict[str, Any]:
    """Retrieves details of a pull request and synchronizes local lifecycle tracking."""
    try:
        synced = pr_service.sync_pull_request(repository, number)
        gh_pr = github_client.get_pull_request(repository, number)
        return {
            "pull_request": gh_pr.model_dump(),
            "synchronized": synced.model_dump(),
        }
    except GitHubPRNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/pull-requests/{number}/diff")
def get_pull_request_diff(
    number: int,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> dict[str, Any]:
    """Retrieves raw diff and structured changed files for a pull request."""
    try:
        diff_text = github_client.get_pull_request_diff(repository, number)
        files = github_client.get_pull_request_files(repository, number)
        return {
            "pr_number": number,
            "diff": diff_text,
            "files": [f.model_dump() for f in files],
        }
    except GitHubPRNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/pull-requests/{number}/review")
def review_pull_request(
    number: int,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> dict[str, Any]:
    """Executes AI static code review on the real GitHub PR diff."""
    try:
        review = pr_service.review_pull_request(repository, number)
        synced = github_repo.get_synced_pr(repository, number)
        return {
            "review": review.model_dump(),
            "synchronized": synced.model_dump() if synced else None,
        }
    except GitHubPRNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/pull-requests/{number}/comments")
def publish_lab_comment(
    number: int,
    payload: PublishCommentRequest,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> dict[str, Any]:
    """Publishes deterministic Engineering Lab verification report comment to GitHub."""
    try:
        body = pr_service.publish_lab_comment(
            repository=repository,
            pr_number=number,
            commit_sha=payload.commit_sha,
            lab_status=payload.lab_status,
            ci_status=payload.ci_status,
            evidence_ids=payload.evidence_ids,
            release_readiness_state=payload.release_readiness_state,
        )
        return {"success": True, "comment_body": body}
    except StaleCommitVerificationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/actions/{commit_sha}")
def get_ci_status(
    commit_sha: str,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> dict[str, Any]:
    """Evaluates GitHub Actions CI gate for the commit SHA."""
    passed, status, run = actions_service.verify_ci_gate(repository, commit_sha)
    return {
        "commit_sha": commit_sha,
        "gate_status": status,
        "passed": passed,
        "workflow_run": run.model_dump() if run else None,
    }


@router.get("/checks/{commit_sha}")
def get_checks(
    commit_sha: str,
    repository: str = Query(default_factory=lambda: os.environ.get("GITHUB_REPOSITORY", "antigravity/engineering-lab")),
) -> list[dict[str, Any]]:
    """Lists GitHub check runs for a commit SHA."""
    try:
        checks = github_client.list_check_runs(repository, commit_sha)
        return [c.model_dump() for c in checks]
    except GitHubError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/webhooks")
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """
    Receives and processes GitHub webhook deliveries.
    Enforces HMAC-SHA256 signature verification and delivery idempotency.
    """
    body_bytes = await request.body()
    try:
        webhook_service.verify_signature(body_bytes, x_hub_signature_256)
    except GitHubWebhookVerificationError as e:
        raise HTTPException(status_code=401, detail=str(e))

    payload = await request.json()
    result = webhook_service.process_webhook_event(
        event_type=x_github_event,
        delivery_id=x_github_delivery,
        payload=payload,
    )
    return result
