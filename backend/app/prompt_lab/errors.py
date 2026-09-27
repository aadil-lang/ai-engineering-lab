"""Prompt Reliability Lab error types."""

class PromptLabError(Exception):
    """Base exception for all Prompt Lab errors."""
    pass


class PromptNotFoundError(PromptLabError):
    """Raised when a prompt definition cannot be found."""
    pass


class PromptVersionNotFoundError(PromptLabError):
    """Raised when a specific prompt version cannot be found."""
    pass


class PromptVersionImmutableError(PromptLabError):
    """Raised when attempting to modify a frozen or evaluated prompt version."""
    pass


class EvaluationSuiteNotFoundError(PromptLabError):
    """Raised when an evaluation suite cannot be found."""
    pass


class EvaluationCaseNotFoundError(PromptLabError):
    """Raised when an evaluation case cannot be found."""
    pass


class EvaluationRunNotFoundError(PromptLabError):
    """Raised when an evaluation run cannot be found."""
    pass


class InvalidPromptTemplateError(PromptLabError):
    """Raised when a prompt template has invalid syntax or missing required variables."""
    pass


class EvaluationSnapshotTamperedError(PromptLabError):
    """Raised when an immutable evaluation snapshot hash does not match content."""
    pass


class CandidateNotFoundError(PromptLabError):
    """Raised when a prompt improvement candidate cannot be found."""
    pass


class UnsupportedEvaluatorStrategyError(PromptLabError):
    """Raised when an evaluator strategy is not supported."""
    pass
