class GitHubError(Exception):
    """Base exception for all GitHub-related operations."""
    pass


class GitHubAuthenticationError(GitHubError):
    """Raised when GitHub token or credentials are invalid or missing."""
    pass


class GitHubRepositoryNotFoundError(GitHubError):
    """Raised when the requested GitHub repository does not exist or is inaccessible."""
    pass


class GitHubPRNotFoundError(GitHubError):
    """Raised when a pull request cannot be found by number or repository."""
    pass


class GitHubCommitNotFoundError(GitHubError):
    """Raised when a commit SHA is not found on the remote repository."""
    pass


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubWebhookVerificationError(GitHubError):
    """Raised when a webhook signature fails HMAC verification."""
    pass


class StaleCommitVerificationError(GitHubError):
    """Raised when attempting to verify or apply a verification to a stale or mismatched commit SHA."""
    pass
