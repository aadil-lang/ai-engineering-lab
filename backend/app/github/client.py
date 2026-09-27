import os
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Any
import httpx

from backend.app.github.models import (
    GitHubRepository,
    GitHubBranch,
    GitHubCommit,
    GitHubPullRequest,
    GitHubPullRequestFile,
    GitHubWorkflowRun,
    GitHubCheckRun,
    GitHubPRComment,
    GitHubState,
    GitHubRunStatus,
    GitHubRunConclusion,
)
from backend.app.github.errors import (
    GitHubError,
    GitHubAuthenticationError,
    GitHubRepositoryNotFoundError,
    GitHubPRNotFoundError,
    GitHubCommitNotFoundError,
    GitHubRateLimitError,
)


def redact_secrets(text: str) -> str:
    """Safely scrubs potential GitHub tokens or bearer credentials from strings."""
    if not text:
        return text
    # Pattern matching ghp_, github_pat_, or Bearer tokens
    scrubbed = re.sub(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})", "[REDACTED_GITHUB_TOKEN]", text)
    scrubbed = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_BEARER_TOKEN]", scrubbed)
    return scrubbed


class GitHubClient:
    """
    Client for interacting with the GitHub REST API v3 (2022-11-28).
    Strictly read-oriented with narrow, allow-listed comment creation.
    Never exposes credentials or tokens in string representation or errors.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = (base_url or os.environ.get("GITHUB_API_URL", "https://api.github.com")).rstrip("/")
        self._transport = transport
        self._client: Optional[httpx.Client] = None

    def __repr__(self) -> str:
        has_token = bool(self._token)
        return f"<GitHubClient base_url='{self.base_url}' authenticated={has_token}>"

    def __str__(self) -> str:
        return self.__repr__()

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Antigravity-EngineeringLab/1.0",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=15.0,
                transport=self._transport,
            )
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def _handle_error_response(self, response: httpx.Response, context: str):
        status = response.status_code
        try:
            body = response.json()
            message = redact_secrets(body.get("message", response.text))
        except Exception:
            message = redact_secrets(response.text)

        if status in (401, 403):
            if "rate limit" in message.lower():
                raise GitHubRateLimitError(f"GitHub API rate limit exceeded: {message}")
            raise GitHubAuthenticationError(f"GitHub authentication error ({status}): {message}")
        elif status == 404:
            if "pull" in context.lower():
                raise GitHubPRNotFoundError(f"Pull request not found in {context}: {message}")
            elif "commit" in context.lower():
                raise GitHubCommitNotFoundError(f"Commit not found in {context}: {message}")
            raise GitHubRepositoryNotFoundError(f"Repository resource not found ({context}): {message}")
        elif status == 429:
            raise GitHubRateLimitError(f"GitHub rate limit exceeded: {message}")
        else:
            raise GitHubError(f"GitHub API error {status} for {context}: {message}")

    def get_repository(self, repo: str) -> GitHubRepository:
        """Retrieves metadata for an owner/repo repository."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}")
        if res.status_code != 200:
            self._handle_error_response(res, f"repository {repo}")
        d = res.json()
        return GitHubRepository(
            github_id=d["id"],
            owner=d["owner"]["login"],
            name=d["name"],
            full_name=d["full_name"],
            default_branch=d.get("default_branch", "main"),
            is_private=d.get("private", False),
            html_url=d["html_url"],
            description=d.get("description"),
        )

    def get_branch(self, repo: str, branch: str) -> GitHubBranch:
        """Retrieves details of a specific branch in the repository."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/branches/{branch}")
        if res.status_code != 200:
            self._handle_error_response(res, f"branch {branch} in {repo}")
        d = res.json()
        return GitHubBranch(
            name=d["name"],
            commit_sha=d["commit"]["sha"],
            is_protected=d.get("protected", False),
        )

    def get_commit(self, repo: str, commit_sha: str) -> GitHubCommit:
        """Retrieves detailed commit provenance by SHA."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/commits/{commit_sha}")
        if res.status_code != 200:
            self._handle_error_response(res, f"commit {commit_sha} in {repo}")
        d = res.json()
        parents = [p["sha"] for p in d.get("parents", [])]
        commit_info = d.get("commit", {})
        author_info = commit_info.get("author", {})
        return GitHubCommit(
            commit_sha=d["sha"],
            parent_commit_shas=parents,
            author_name=author_info.get("name", "Unknown"),
            author_email=author_info.get("email", "unknown@example.com"),
            timestamp=author_info.get("date", datetime.now(timezone.utc).isoformat()),
            message=commit_info.get("message", ""),
            tree_sha=commit_info.get("tree", {}).get("sha"),
        )

    def list_pull_requests(self, repo: str, state: str = "open") -> list[GitHubPullRequest]:
        """Lists pull requests for a repository."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/pulls", params={"state": state})
        if res.status_code != 200:
            self._handle_error_response(res, f"pull requests for {repo}")
        items = res.json()
        prs = []
        for d in items:
            prs.append(
                GitHubPullRequest(
                    github_id=d["id"],
                    number=d["number"],
                    title=d["title"],
                    body=d.get("body") or "",
                    state=GitHubState(d.get("state", "open")),
                    head_branch=d["head"]["ref"],
                    base_branch=d["base"]["ref"],
                    head_sha=d["head"]["sha"],
                    base_sha=d["base"]["sha"],
                    author_login=d["user"]["login"],
                    html_url=d["html_url"],
                    is_draft=d.get("draft", False),
                    created_at=d["created_at"],
                    updated_at=d["updated_at"],
                    merged_at=d.get("merged_at"),
                    closed_at=d.get("closed_at"),
                )
            )
        return prs

    def get_pull_request(self, repo: str, pr_number: int) -> GitHubPullRequest:
        """Retrieves a single pull request by number."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/pulls/{pr_number}")
        if res.status_code != 200:
            self._handle_error_response(res, f"pull request #{pr_number} in {repo}")
        d = res.json()
        return GitHubPullRequest(
            github_id=d["id"],
            number=d["number"],
            title=d["title"],
            body=d.get("body") or "",
            state=GitHubState(d.get("state", "open")),
            head_branch=d["head"]["ref"],
            base_branch=d["base"]["ref"],
            head_sha=d["head"]["sha"],
            base_sha=d["base"]["sha"],
            author_login=d["user"]["login"],
            html_url=d["html_url"],
            is_draft=d.get("draft", False),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            merged_at=d.get("merged_at"),
            closed_at=d.get("closed_at"),
        )

    def get_pull_request_diff(self, repo: str, pr_number: int) -> str:
        """Retrieves raw unified diff for a pull request."""
        client = self._get_client()
        # Accept diff header
        headers = {"Accept": "application/vnd.github.v3.diff"}
        res = client.get(f"/repos/{repo}/pulls/{pr_number}", headers=headers)
        if res.status_code != 200:
            self._handle_error_response(res, f"diff for pull request #{pr_number} in {repo}")
        return res.text

    def get_pull_request_files(self, repo: str, pr_number: int) -> list[GitHubPullRequestFile]:
        """Retrieves structured changed files in a pull request."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/pulls/{pr_number}/files")
        if res.status_code != 200:
            self._handle_error_response(res, f"files for pull request #{pr_number} in {repo}")
        items = res.json()
        files = []
        for f in items:
            files.append(
                GitHubPullRequestFile(
                    sha=f.get("sha", ""),
                    filename=f["filename"],
                    status=f.get("status", "modified"),
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                    changes=f.get("changes", 0),
                    patch=f.get("patch"),
                )
            )
        return files

    def list_workflow_runs(self, repo: str, commit_sha: Optional[str] = None) -> list[GitHubWorkflowRun]:
        """Lists GitHub Actions workflow runs for the repository, optionally filtered by commit SHA."""
        client = self._get_client()
        params = {}
        if commit_sha:
            params["head_sha"] = commit_sha
        res = client.get(f"/repos/{repo}/actions/runs", params=params)
        if res.status_code != 200:
            self._handle_error_response(res, f"workflow runs for {repo}")
        data = res.json()
        runs = []
        for r in data.get("workflow_runs", []):
            conclusion_val = r.get("conclusion")
            runs.append(
                GitHubWorkflowRun(
                    github_run_id=r["id"],
                    workflow_name=r.get("name", "CI"),
                    head_sha=r["head_sha"],
                    head_branch=r.get("head_branch") or "main",
                    status=GitHubRunStatus(r.get("status", "completed")),
                    conclusion=GitHubRunConclusion(conclusion_val) if conclusion_val else None,
                    html_url=r["html_url"],
                    started_at=r.get("run_started_at") or r.get("created_at"),
                    completed_at=r.get("updated_at") if r.get("status") == "completed" else None,
                    duration_ms=0,
                    jobs_summary=f"{r.get('run_attempt', 1)} attempts",
                )
            )
        return runs

    def get_workflow_run(self, repo: str, run_id: int) -> GitHubWorkflowRun:
        """Retrieves details of a specific GitHub Actions workflow run."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/actions/runs/{run_id}")
        if res.status_code != 200:
            self._handle_error_response(res, f"workflow run #{run_id} in {repo}")
        r = res.json()
        conclusion_val = r.get("conclusion")
        return GitHubWorkflowRun(
            github_run_id=r["id"],
            workflow_name=r.get("name", "CI"),
            head_sha=r["head_sha"],
            head_branch=r.get("head_branch") or "main",
            status=GitHubRunStatus(r.get("status", "completed")),
            conclusion=GitHubRunConclusion(conclusion_val) if conclusion_val else None,
            html_url=r["html_url"],
            started_at=r.get("run_started_at") or r.get("created_at"),
            completed_at=r.get("updated_at") if r.get("status") == "completed" else None,
            duration_ms=0,
            jobs_summary=f"{r.get('run_attempt', 1)} attempts",
        )

    def list_check_runs(self, repo: str, commit_sha: str) -> list[GitHubCheckRun]:
        """Lists GitHub check runs for a specific commit SHA."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/commits/{commit_sha}/check-runs")
        if res.status_code != 200:
            self._handle_error_response(res, f"check runs for {commit_sha} in {repo}")
        data = res.json()
        checks = []
        for c in data.get("check_runs", []):
            checks.append(
                GitHubCheckRun(
                    github_check_id=c["id"],
                    name=c["name"],
                    head_sha=c["head_sha"],
                    status=c.get("status", "completed"),
                    conclusion=c.get("conclusion"),
                    started_at=c.get("started_at", datetime.now(timezone.utc).isoformat()),
                    completed_at=c.get("completed_at"),
                )
            )
        return checks

    def list_pr_comments(self, repo: str, pr_number: int) -> list[GitHubPRComment]:
        """Lists issue comments on a pull request."""
        client = self._get_client()
        res = client.get(f"/repos/{repo}/issues/{pr_number}/comments")
        if res.status_code != 200:
            self._handle_error_response(res, f"comments for PR #{pr_number} in {repo}")
        items = res.json()
        comments = []
        for c in items:
            body_text = c.get("body", "")
            # Extract embedded idempotency key if present: <!-- antigravity-idempotency: KEY -->
            m = re.search(r"<!-- antigravity-idempotency:\s*([a-zA-Z0-9_\-\.:#]+)\s*-->", body_text)
            key = m.group(1) if m else None
            comments.append(
                GitHubPRComment(
                    github_comment_id=c["id"],
                    pr_number=pr_number,
                    body=body_text,
                    author_login=c["user"]["login"],
                    created_at=c["created_at"],
                    updated_at=c["updated_at"],
                    idempotency_key=key,
                )
            )
        return comments

    def create_pr_comment(
        self,
        repo: str,
        pr_number: int,
        body: str,
        idempotency_key: Optional[str] = None,
    ) -> GitHubPRComment:
        """
        Creates a comment on a pull request with duplicate detection.
        If idempotency_key is provided and already exists in PR comments, returns existing comment.
        """
        # Scrub any potential secrets before sending
        safe_body = redact_secrets(body)

        if idempotency_key:
            existing_comments = self.list_pr_comments(repo, pr_number)
            for c in existing_comments:
                if c.idempotency_key == idempotency_key:
                    return c
            safe_body = f"{safe_body}\n\n<!-- antigravity-idempotency: {idempotency_key} -->"

        client = self._get_client()
        res = client.post(f"/repos/{repo}/issues/{pr_number}/comments", json={"body": safe_body})
        if res.status_code not in (200, 201):
            self._handle_error_response(res, f"create comment on PR #{pr_number} in {repo}")
        c = res.json()
        return GitHubPRComment(
            github_comment_id=c["id"],
            pr_number=pr_number,
            body=safe_body,
            author_login=c["user"]["login"],
            created_at=c["created_at"],
            updated_at=c["updated_at"],
            idempotency_key=idempotency_key,
        )
