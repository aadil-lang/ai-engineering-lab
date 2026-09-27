from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GitFileStatus(str, Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    UNTRACKED = "UNTRACKED"


class GitChangedFile(BaseModel):
    path: str
    status: GitFileStatus
    additions: int = 0
    deletions: int = 0


class GitStatus(BaseModel):
    repository: str
    branch: str
    commit_sha: str
    parent_commit_sha: Optional[str] = None
    is_clean: bool
    changed_files: list[GitChangedFile] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    ahead: int = 0
    behind: int = 0


class GitCommit(BaseModel):
    commit_sha: str
    parent_commit_sha: Optional[str] = None
    author: str
    email: str
    timestamp: str
    message: str
    files_changed: list[str] = Field(default_factory=list)


class GitFileDiff(BaseModel):
    path: str
    status: GitFileStatus
    additions: int = 0
    deletions: int = 0
    patch: str = ""


class GitDiff(BaseModel):
    repository: str
    base_sha: str
    head_sha: str
    files: list[GitFileDiff] = Field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
