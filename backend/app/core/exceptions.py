class PlatformException(Exception):
    """Base exception for AI Reliability Platform."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class NotFoundException(PlatformException):
    """Resource not found."""
    pass

class ValidationException(PlatformException):
    """Input validation error."""
    pass

class ExecutionException(PlatformException):
    """Test execution error."""
    pass

class StorageException(PlatformException):
    """Storage or persistence error."""
    pass
