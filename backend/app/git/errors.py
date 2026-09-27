class GitError(Exception):
    """Base exception for all Git operations."""
    pass


class RepositoryNotFoundError(GitError):
    """Raised when repository directory is not found or not a valid Git repository."""
    pass


class CommitNotFoundError(GitError):
    """Raised when a specific commit SHA does not exist in the repository."""
    pass


class GitExecutionError(GitError):
    """Raised when a git CLI command fails during execution."""
    def __init__(self, command: str, returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Git command '{command}' failed (code {returncode}): {stderr}")
