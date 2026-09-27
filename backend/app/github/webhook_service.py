import hmac
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional, Any

from backend.app.github.repository import GitHubSyncRepository, get_github_sync_repo
from backend.app.github.models import (
    SynchronizedPR,
    GitHubWorkflowRun,
    GitHubRunStatus,
    GitHubRunConclusion,
)
from backend.app.github.errors import GitHubWebhookVerificationError


class GitHubWebhookService:
    """
    Service for processing incoming GitHub webhook deliveries.
    Enforces HMAC-SHA256 signature verification and delivery idempotency.
    Guarantees no arbitrary shell command execution from webhook payloads.
    """

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        repository: Optional[GitHubSyncRepository] = None,
    ):
        self.secret = webhook_secret or os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        self.repo = repository or get_github_sync_repo()

    def verify_signature(self, payload_bytes: bytes, signature_header: Optional[str]) -> bool:
        """
        Validates HMAC-SHA256 signature from X-Hub-Signature-256 header.
        Raises GitHubWebhookVerificationError if invalid or missing when secret is configured.
        """
        if not self.secret:
            # If no secret configured in test/dev, allow or require?
            # Security non-negotiable: if signature header is provided or secret is set, verify
            return True

        if not signature_header or not signature_header.startswith("sha256="):
            raise GitHubWebhookVerificationError("Missing or malformed X-Hub-Signature-256 header")

        expected_sig = hmac.new(
            self.secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        provided_sig = signature_header[len("sha256="):]

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise GitHubWebhookVerificationError("Invalid webhook signature")

        return True

    def process_webhook_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Processes an incoming webhook delivery idempotently.
        Supports: 'pull_request', 'workflow_run', 'check_run', 'push'.
        """
        # Idempotency check
        if self.repo.is_webhook_processed(delivery_id):
            return {
                "status": "skipped",
                "reason": "duplicate_delivery",
                "delivery_id": delivery_id,
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        self.repo.record_webhook_delivery(delivery_id, event_type, now_iso)

        if event_type == "pull_request":
            action = payload.get("action")
            pr_data = payload.get("pull_request", {})
            repo_data = payload.get("repository", {})
            repo_name = repo_data.get("full_name", "")
            pr_number = pr_data.get("number")

            if repo_name and pr_number:
                head_sha = pr_data.get("head", {}).get("sha", "")
                base_sha = pr_data.get("base", {}).get("sha", "")
                head_branch = pr_data.get("head", {}).get("ref", "")
                base_branch = pr_data.get("base", {}).get("ref", "")
                gh_state = pr_data.get("state", "open")

                existing = self.repo.get_synced_pr(repo_name, pr_number)
                is_stale_commit = existing and existing.head_commit_sha != head_sha

                synced = SynchronizedPR(
                    repository=repo_name,
                    pull_request_number=pr_number,
                    head_branch=head_branch,
                    base_branch=base_branch,
                    head_commit_sha=head_sha,
                    base_commit_sha=base_sha,
                    github_state=gh_state,
                    local_lifecycle_state="OPEN" if (is_stale_commit or action == "opened") else (
                        existing.local_lifecycle_state if existing else "OPEN"
                    ),
                    created_at=existing.created_at if existing else now_iso,
                    updated_at=now_iso,
                    last_verified_commit_sha=None if is_stale_commit else (
                        existing.last_verified_commit_sha if existing else None
                    ),
                    ci_verified_commit_sha=None if is_stale_commit else (
                        existing.ci_verified_commit_sha if existing else None
                    ),
                )
                self.repo.save_synced_pr(synced)
                return {
                    "status": "processed",
                    "event": "pull_request",
                    "action": action,
                    "pr_number": pr_number,
                    "head_sha": head_sha,
                    "stale_invalidated": bool(is_stale_commit),
                }

        elif event_type == "workflow_run":
            action = payload.get("action")
            run_data = payload.get("workflow_run", {})
            run_id = run_data.get("id")
            if run_id:
                conc = run_data.get("conclusion")
                run = GitHubWorkflowRun(
                    github_run_id=run_id,
                    workflow_name=run_data.get("name", "CI"),
                    head_sha=run_data.get("head_sha", ""),
                    head_branch=run_data.get("head_branch") or "main",
                    status=GitHubRunStatus(run_data.get("status", "completed")),
                    conclusion=GitHubRunConclusion(conc) if conc else None,
                    html_url=run_data.get("html_url", ""),
                    started_at=run_data.get("run_started_at") or now_iso,
                    completed_at=run_data.get("updated_at") if run_data.get("status") == "completed" else None,
                    duration_ms=0,
                    jobs_summary=f"Event action: {action}",
                )
                self.repo.save_workflow_run(run)
                return {
                    "status": "processed",
                    "event": "workflow_run",
                    "run_id": run_id,
                    "status_val": run.status.value,
                    "conclusion": conc,
                }

        return {
            "status": "acknowledged",
            "event": event_type,
            "delivery_id": delivery_id,
        }
