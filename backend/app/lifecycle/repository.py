import sqlite3
from typing import Optional
from pathlib import Path
from backend.app.lifecycle.models import PullRequest, PRReview, CIRun, ReleaseReadiness, PRStatus


class LifecycleRepository:
    """
    Storage repository for Pull Requests, AI Code Reviews, CI runs, and Release Readiness records.
    Provides in-memory caching with SQLite backing.
    """

    def __init__(self, db_path: str = "backend/data/reliability_platform.db"):
        self.db_path = db_path
        self._prs: dict[str, PullRequest] = {}
        self._reviews: dict[str, PRReview] = {}
        self._ci_runs: dict[str, CIRun] = {}
        self._readiness: dict[str, ReleaseReadiness] = {}
        self._conn = sqlite3.connect(":memory:", check_same_thread=False) if db_path == ":memory:" else None
        self._init_tables()

    def _get_conn(self):
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Ensures SQLite tables exist for lifecycle persistence."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pull_requests (
                id TEXT PRIMARY KEY,
                repository TEXT,
                number INTEGER,
                title TEXT,
                description TEXT,
                source_branch TEXT,
                target_branch TEXT,
                head_sha TEXT,
                base_sha TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                merged_at TEXT,
                closed_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ci_runs (
                id TEXT PRIMARY KEY,
                commit_sha TEXT,
                workflow TEXT,
                status TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_ms INTEGER,
                tests_total INTEGER,
                tests_passed INTEGER,
                tests_failed INTEGER,
                artifacts_json TEXT,
                logs TEXT
            )
        """)
        conn.commit()
        if self._conn is None:
            conn.close()

    # --- PR Operations ---
    def save_pr(self, pr: PullRequest):
        self._prs[pr.id] = pr
        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO pull_requests (
                id, repository, number, title, description,
                source_branch, target_branch, head_sha, base_sha,
                status, created_at, updated_at, merged_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr.id, pr.repository, pr.number, pr.title, pr.description,
            pr.source_branch, pr.target_branch, pr.head_sha, pr.base_sha,
            pr.status.value, pr.created_at, pr.updated_at, pr.merged_at, pr.closed_at
        ))
        conn.commit()
        if self._conn is None:
            conn.close()

    def get_pr(self, pr_id: str) -> Optional[PullRequest]:
        if pr_id in self._prs:
            return self._prs[pr_id]
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pull_requests WHERE id = ?", (pr_id,))
        row = cursor.fetchone()
        pr = None
        if row:
            pr = PullRequest(
                id=row["id"],
                repository=row["repository"],
                number=row["number"],
                title=row["title"],
                description=row["description"],
                source_branch=row["source_branch"],
                target_branch=row["target_branch"],
                head_sha=row["head_sha"],
                base_sha=row["base_sha"],
                status=PRStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                merged_at=row["merged_at"],
                closed_at=row["closed_at"],
            )
            self._prs[pr.id] = pr
        if self._conn is None:
            conn.close()
        return pr

    def list_prs(self, repository: Optional[str] = None) -> list[PullRequest]:
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if repository:
            cursor.execute("SELECT * FROM pull_requests WHERE repository = ? ORDER BY number DESC", (repository,))
        else:
            cursor.execute("SELECT * FROM pull_requests ORDER BY number DESC")
        rows = cursor.fetchall()
        prs = []
        for row in rows:
            pr = PullRequest(
                id=row["id"],
                repository=row["repository"],
                number=row["number"],
                title=row["title"],
                description=row["description"],
                source_branch=row["source_branch"],
                target_branch=row["target_branch"],
                head_sha=row["head_sha"],
                base_sha=row["base_sha"],
                status=PRStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                merged_at=row["merged_at"],
                closed_at=row["closed_at"],
            )
            self._prs[pr.id] = pr
            prs.append(pr)
        if self._conn is None:
            conn.close()
        return prs

    # --- Review Operations ---
    def save_review(self, review: PRReview):
        self._reviews[review.review_id] = review

    def get_review(self, review_id: str) -> Optional[PRReview]:
        return self._reviews.get(review_id)

    def get_review_by_pr(self, pr_id: str) -> Optional[PRReview]:
        for r in self._reviews.values():
            if r.pr_id == pr_id:
                return r
        return None

    def get_reviews_for_pr(self, pr_id: str) -> list[PRReview]:
        return [r for r in self._reviews.values() if r.pr_id == pr_id]

    # --- CI Run Operations ---
    def save_ci_run(self, run: CIRun):
        self._ci_runs[run.id] = run

    def get_ci_run(self, run_id: str) -> Optional[CIRun]:
        return self._ci_runs.get(run_id)

    def get_ci_runs_for_commit(self, commit_sha: str) -> list[CIRun]:
        return [r for r in self._ci_runs.values() if r and r.commit_sha == commit_sha]

    def get_latest_ci_run_for_commit(self, commit_sha: str) -> Optional[CIRun]:
        runs = [r for r in self._ci_runs.values() if r and r.commit_sha == commit_sha]
        if not runs:
            return None
        return sorted(runs, key=lambda x: x.started_at, reverse=True)[0]

    # --- Release Readiness Operations ---
    def save_readiness(self, readiness: ReleaseReadiness):
        self._readiness[readiness.commit_sha] = readiness

    def get_readiness(self, commit_sha: str) -> Optional[ReleaseReadiness]:
        return self._readiness.get(commit_sha)


_default_lifecycle_repo: Optional[LifecycleRepository] = None


def get_lifecycle_repo() -> LifecycleRepository:
    global _default_lifecycle_repo
    if _default_lifecycle_repo is None:
        _default_lifecycle_repo = LifecycleRepository()
    return _default_lifecycle_repo

