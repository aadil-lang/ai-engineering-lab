import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from backend.app.git.models import (
    GitStatus,
    GitCommit,
    GitDiff,
    GitFileDiff,
    GitChangedFile,
    GitFileStatus,
)
from backend.app.git.errors import (
    GitError,
    RepositoryNotFoundError,
    CommitNotFoundError,
    GitExecutionError,
)


class GitService:
    """
    Canonical Git Service for reading repository state, commits, diffs, and provenance.
    Strictly read-oriented to prevent accidental mutations via agent operations.
    """

    def __init__(self, repo_path: str | Path | None = None):
        if repo_path is None:
            # Default to project root
            self.repo_path = Path(__file__).resolve().parents[3]
        else:
            self.repo_path = Path(repo_path).resolve()

        self.repo_name = self.repo_path.name

    def _run_git(self, args: list[str]) -> str:
        """Executes a git command safely with timeouts."""
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=15,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            raise GitError("git executable not found in system PATH")
        except Exception as e:
            raise GitError(f"Failed to execute git: {e}")

        if res.returncode != 0:
            if "not a git repository" in res.stderr.lower():
                raise RepositoryNotFoundError(f"Not a git repository: {self.repo_path}")
            raise GitExecutionError(" ".join(cmd), res.returncode, res.stderr.strip())

        return res.stdout.strip()

    def is_git_repository(self) -> bool:
        """Checks whether the target path is inside a Git repository."""
        try:
            out = self._run_git(["rev-parse", "--is-inside-work-tree"])
            return out.strip().lower() == "true"
        except (RepositoryNotFoundError, GitExecutionError, GitError):
            return False

    def get_current_branch(self) -> str:
        """Returns current checked out branch name or 'HEAD'."""
        try:
            branch = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
            return branch if branch else "HEAD"
        except Exception:
            return "unknown"

    def get_head_commit_sha(self) -> str:
        """Returns full 40-character SHA of current HEAD commit."""
        return self._run_git(["rev-parse", "HEAD"])

    def get_parent_commit_sha(self, commit_sha: str = "HEAD") -> Optional[str]:
        """Returns the parent commit SHA of the specified commit."""
        try:
            parent = self._run_git(["rev-parse", f"{commit_sha}^"])
            return parent if parent else None
        except Exception:
            return None

    def get_status(self) -> GitStatus:
        """Returns detailed Git status: branch, clean/dirty state, changed files."""
        if not self.is_git_repository():
            raise RepositoryNotFoundError(f"Not a git repository: {self.repo_path}")

        branch = self.get_current_branch()
        commit_sha = self.get_head_commit_sha()
        parent_sha = self.get_parent_commit_sha(commit_sha)

        # Parse porcelain status
        raw_status = self._run_git(["status", "--porcelain"])
        changed_files: list[GitChangedFile] = []
        untracked_files: list[str] = []

        if raw_status:
            for line in raw_status.splitlines():
                if len(line) < 3:
                    continue
                code = line[:2]
                path = line[3:].strip()
                if " -> " in path:
                    path = path.split(" -> ")[-1].strip()

                if code == "??":
                    untracked_files.append(path)
                elif "A" in code:
                    changed_files.append(GitChangedFile(path=path, status=GitFileStatus.ADDED))
                elif "D" in code:
                    changed_files.append(GitChangedFile(path=path, status=GitFileStatus.DELETED))
                elif "R" in code:
                    changed_files.append(GitChangedFile(path=path, status=GitFileStatus.RENAMED))
                else:
                    changed_files.append(GitChangedFile(path=path, status=GitFileStatus.MODIFIED))

        is_clean = len(changed_files) == 0 and len(untracked_files) == 0

        return GitStatus(
            repository=self.repo_name,
            branch=branch,
            commit_sha=commit_sha,
            parent_commit_sha=parent_sha,
            is_clean=is_clean,
            changed_files=changed_files,
            untracked_files=untracked_files,
            ahead=0,
            behind=0,
        )

    def get_commit(self, commit_sha: str = "HEAD") -> GitCommit:
        """Retrieves details of a specific commit by SHA."""
        try:
            # Format: HASH%x1fPARENT%x1fAUTHOR%x1fEMAIL%x1fDATE%x1fSUBJECT
            out = self._run_git([
                "show",
                "-s",
                "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%cI%x1f%s",
                commit_sha,
            ])
        except GitExecutionError as e:
            if "unknown revision" in e.stderr.lower() or "bad object" in e.stderr.lower():
                raise CommitNotFoundError(f"Commit not found: {commit_sha}")
            raise

        parts = out.split("\x1f")
        if len(parts) < 6:
            raise GitError(f"Unexpected commit format for {commit_sha}: {out}")

        sha, parents, author, email, timestamp, message = parts
        parent_sha = parents.split()[0] if parents.strip() else None

        # Get list of changed files in this commit
        files_out = self._run_git(["show", "--stat", "--name-only", "--oneline", commit_sha])
        files_lines = files_out.splitlines()[1:] if files_out else []
        files_changed = [line.strip() for line in files_lines if line.strip()]

        return GitCommit(
            commit_sha=sha,
            parent_commit_sha=parent_sha,
            author=author,
            email=email,
            timestamp=timestamp,
            message=message,
            files_changed=files_changed,
        )

    def get_recent_commits(self, limit: int = 10) -> list[GitCommit]:
        """Retrieves a list of recent commits in reverse chronological order."""
        out = self._run_git([
            "log",
            f"-n{limit}",
            "--format=%H",
        ])
        commits: list[GitCommit] = []
        for sha in out.splitlines():
            sha = sha.strip()
            if sha:
                commits.append(self.get_commit(sha))
        return commits

    def get_diff(self, base_sha: Optional[str] = None, head_sha: Optional[str] = None) -> GitDiff:
        """
        Returns structured diff between base_sha and head_sha (or uncommitted changes if none provided).
        """
        args = ["diff"]
        if base_sha and head_sha:
            args.extend([f"{base_sha}..{head_sha}"])
        elif base_sha:
            args.append(base_sha)

        raw_diff = self._run_git(args)
        files = self._parse_diff(raw_diff)

        total_add = sum(f.additions for f in files)
        total_del = sum(f.deletions for f in files)

        current_head = head_sha or self.get_head_commit_sha()
        current_base = base_sha or self.get_parent_commit_sha(current_head) or current_head

        return GitDiff(
            repository=self.repo_name,
            base_sha=current_base,
            head_sha=current_head,
            files=files,
            total_additions=total_add,
            total_deletions=total_del,
        )

    def _parse_diff(self, diff_text: str) -> list[GitFileDiff]:
        """Parses unified diff into per-file diff models."""
        file_diffs: list[GitFileDiff] = []
        if not diff_text.strip():
            return file_diffs

        # Split on "diff --git"
        chunks = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk or not chunk.startswith("diff --git"):
                continue

            lines = chunk.splitlines()
            header = lines[0]
            # e.g. diff --git a/backend/app/main.py b/backend/app/main.py
            m = re.match(r"diff --git a/(.*?) b/(.*)", header)
            path = m.group(2) if m else "unknown"

            status = GitFileStatus.MODIFIED
            if any(l.startswith("new file mode") for l in lines):
                status = GitFileStatus.ADDED
            elif any(l.startswith("deleted file mode") for l in lines):
                status = GitFileStatus.DELETED

            additions = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
            deletions = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))

            file_diffs.append(
                GitFileDiff(
                    path=path,
                    status=status,
                    additions=additions,
                    deletions=deletions,
                    patch=chunk,
                )
            )

        return file_diffs
