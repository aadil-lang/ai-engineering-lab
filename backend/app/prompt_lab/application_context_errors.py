from backend.app.prompt_lab.errors import PromptLabError


class ApplicationContextNotFoundError(PromptLabError):
    """Raised when an application manifest or evaluation context cannot be found."""
    pass


class PromptBindingMismatchError(PromptLabError):
    """Raised when prompt binding does not match application context."""
    pass


class PromptVersionMismatchError(PromptLabError):
    """Raised when prompt version diverges from expected context version."""
    pass


class GitContextMismatchError(PromptLabError):
    """Raised when Git commit SHA in context does not match expected repository state."""
    pass


class ModelContextMissingError(PromptLabError):
    """Raised when model or model configuration is missing from evaluation context."""
    pass


class EvaluationSuiteContextMismatchError(PromptLabError):
    """Raised when evaluation suite ID or version does not match context."""
    pass


class ContextNotFrozenError(PromptLabError):
    """Raised when attempting an application-level evaluation with an un-frozen context."""
    pass


class ContextIntegrityError(PromptLabError):
    """Raised when an EvaluationContext hash or provenance integrity check fails."""
    pass


class DeclaredPromptRuntimeMismatchError(PromptLabError):
    """Raised when declared prompt version diverges from actual prompt observed at runtime."""
    pass
