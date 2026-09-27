from pathlib import Path
from typing import Optional
from backend.app.git.models import GitStatus, GitCommit, GitDiff
from backend.app.git.service import GitService


class GitRepository:
    """
    Repository wrapper providing access to Git artifacts and caching.
    """

    def __init__(self, service: Optional[GitService] = None):
        self.service = service or GitService()

    def get_status(self) -> GitStatus:
        return self.service.get_status()

    def get_commit(self, sha: str = "HEAD") -> GitCommit:
        return self.service.get_commit(sha)

    def get_diff(self, base_sha: Optional[str] = None, head_sha: Optional[str] = None) -> GitDiff:
        return self.service.get_diff(base_sha, head_sha)
