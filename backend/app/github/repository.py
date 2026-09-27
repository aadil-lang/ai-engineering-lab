import sqlite3
from pathlib import Path
from typing import Optional
from backend.app.github.models import SynchronizedPR, GitHubWorkflowRun, GitHubRunStatus, GitHubRunConclusion


class GitHubSyncRepository:
    """
    Persistence store for GitHub synchronization:
    - Synchronized PR state
    - Cached GitHub Actions workflow runs
    - Webhook event idempotency tracking
    """

    def __init__(self, db_path: str = "backend/data/reliability_platform.db"):
        self.db_path = db_path
        self._prs: dict[str, SynchronizedPR] = {}
        self._runs: dict[str, GitHubWorkflowRun] = {}
        self._processed_events: set[str] = set()
        self._conn = sqlite3.connect(":memory:", check_same_thread=False) if db_path == ":memory:" else None
        self._init_tables()

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Ensures SQLite tables exist for GitHub persistence."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_synced_prs (
                repository TEXT,
                pull_request_number INTEGER,
                head_branch TEXT,
                base_branch TEXT,
                head_commit_sha TEXT,
                base_commit_sha TEXT,
                github_state TEXT,
                local_lifecycle_state TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_verified_commit_sha TEXT,
                ci_verified_commit_sha TEXT,
                PRIMARY KEY (repository, pull_request_number)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_workflow_runs (
                github_run_id INTEGER PRIMARY KEY,
                workflow_name TEXT,
                head_sha TEXT,
                head_branch TEXT,
                status TEXT,
                conclusion TEXT,
                html_url TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_ms INTEGER,
                jobs_summary TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_webhook_deliveries (
                delivery_id TEXT PRIMARY KEY,
                event_type TEXT,
                received_at TEXT
            )
        """)
        conn.commit()
        if self._conn is None:
            conn.close()

    def save_synced_pr(self, pr: SynchronizedPR):
        key = f"{pr.repository}:{pr.pull_request_number}"
        self._prs[key] = pr

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO github_synced_prs (
                repository, pull_request_number, head_branch, base_branch,
                head_commit_sha, base_commit_sha, github_state, local_lifecycle_state,
                created_at, updated_at, last_verified_commit_sha, ci_verified_commit_sha
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr.repository,
            pr.pull_request_number,
            pr.head_branch,
            pr.base_branch,
            pr.head_commit_sha,
            pr.base_commit_sha,
            pr.github_state,
            pr.local_lifecycle_state,
            pr.created_at,
            pr.updated_at,
            pr.last_verified_commit_sha,
            pr.ci_verified_commit_sha,
        ))
        conn.commit()
        if self._conn is None:
            conn.close()

    def get_synced_pr(self, repository: str, pr_number: int) -> Optional[SynchronizedPR]:
        key = f"{repository}:{pr_number}"
        if key in self._prs:
            return self._prs[key]

        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM github_synced_prs WHERE repository = ? AND pull_request_number = ?",
            (repository, pr_number)
        )
        row = cursor.fetchone()
        if not row:
            if self._conn is None:
                conn.close()
            return None

        pr = SynchronizedPR(
            repository=row["repository"],
            pull_request_number=row["pull_request_number"],
            head_branch=row["head_branch"],
            base_branch=row["base_branch"],
            head_commit_sha=row["head_commit_sha"],
            base_commit_sha=row["base_commit_sha"],
            github_state=row["github_state"],
            local_lifecycle_state=row["local_lifecycle_state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_verified_commit_sha=row["last_verified_commit_sha"],
            ci_verified_commit_sha=row["ci_verified_commit_sha"],
        )
        self._prs[key] = pr
        if self._conn is None:
            conn.close()
        return pr

    def list_synced_prs(self, repository: Optional[str] = None) -> list[SynchronizedPR]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if repository:
            cursor.execute("SELECT * FROM github_synced_prs WHERE repository = ? ORDER BY pull_request_number DESC", (repository,))
        else:
            cursor.execute("SELECT * FROM github_synced_prs ORDER BY pull_request_number DESC")
        rows = cursor.fetchall()
        prs = []
        for row in rows:
            pr = SynchronizedPR(
                repository=row["repository"],
                pull_request_number=row["pull_request_number"],
                head_branch=row["head_branch"],
                base_branch=row["base_branch"],
                head_commit_sha=row["head_commit_sha"],
                base_commit_sha=row["base_commit_sha"],
                github_state=row["github_state"],
                local_lifecycle_state=row["local_lifecycle_state"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                last_verified_commit_sha=row["last_verified_commit_sha"],
                ci_verified_commit_sha=row["ci_verified_commit_sha"],
            )
            key = f"{pr.repository}:{pr.pull_request_number}"
            self._prs[key] = pr
            prs.append(pr)
        if self._conn is None:
            conn.close()
        return prs

    def save_workflow_run(self, run: GitHubWorkflowRun):
        self._runs[str(run.github_run_id)] = run

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO github_workflow_runs (
                github_run_id, workflow_name, head_sha, head_branch,
                status, conclusion, html_url, started_at, completed_at,
                duration_ms, jobs_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.github_run_id,
            run.workflow_name,
            run.head_sha,
            run.head_branch,
            run.status.value,
            run.conclusion.value if run.conclusion else None,
            run.html_url,
            run.started_at,
            run.completed_at,
            run.duration_ms,
            run.jobs_summary,
        ))
        conn.commit()
        if self._conn is None:
            conn.close()

    def get_latest_workflow_run_for_commit(self, commit_sha: str) -> Optional[GitHubWorkflowRun]:
        matching = [r for r in self._runs.values() if r.head_sha == commit_sha]
        if matching:
            return sorted(matching, key=lambda x: x.started_at, reverse=True)[0]

        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM github_workflow_runs WHERE head_sha = ? ORDER BY started_at DESC LIMIT 1",
            (commit_sha,)
        )
        row = cursor.fetchone()
        if not row:
            if self._conn is None:
                conn.close()
            return None

        conc = row["conclusion"]
        run = GitHubWorkflowRun(
            github_run_id=row["github_run_id"],
            workflow_name=row["workflow_name"],
            head_sha=row["head_sha"],
            head_branch=row["head_branch"],
            status=GitHubRunStatus(row["status"]),
            conclusion=GitHubRunConclusion(conc) if conc else None,
            html_url=row["html_url"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_ms=row["duration_ms"],
            jobs_summary=row["jobs_summary"],
        )
        if self._conn is None:
            conn.close()
        return run

    def record_webhook_delivery(self, delivery_id: str, event_type: str, received_at: str):
        self._processed_events.add(delivery_id)
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO github_webhook_deliveries (delivery_id, event_type, received_at)
            VALUES (?, ?, ?)
        """, (delivery_id, event_type, received_at))
        conn.commit()
        if self._conn is None:
            conn.close()

    def is_webhook_processed(self, delivery_id: str) -> bool:
        if delivery_id in self._processed_events:
            return True
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM github_webhook_deliveries WHERE delivery_id = ?", (delivery_id,))
        row = cursor.fetchone()
        if self._conn is None:
            conn.close()
        if row:
            self._processed_events.add(delivery_id)
            return True
        return False


_default_github_repo: Optional[GitHubSyncRepository] = None


def get_github_sync_repo() -> GitHubSyncRepository:
    global _default_github_repo
    if _default_github_repo is None:
        _default_github_repo = GitHubSyncRepository()
    return _default_github_repo
