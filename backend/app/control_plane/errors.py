from typing import Any
from backend.app.models.tools import ToolErrorCode, ToolError


class ControlPlaneError(Exception):
    """Base exception for all Reliability Control Plane operations."""

    def __init__(
        self,
        error_code: ToolErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable

    def to_tool_error(self) -> ToolError:
        return ToolError(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            recoverable=self.recoverable,
        )


class ApplicationNotFoundError(ControlPlaneError):
    def __init__(self, application_id: str):
        super().__init__(
            error_code=ToolErrorCode.APPLICATION_NOT_FOUND,
            message=f"Application target '{application_id}' not found in platform registry.",
            details={"application_id": application_id},
            recoverable=False,
        )


class SessionNotFoundError(ControlPlaneError):
    def __init__(self, session_id: str):
        super().__init__(
            error_code=ToolErrorCode.SESSION_NOT_FOUND,
            message=f"Test session '{session_id}' not found or has expired.",
            details={"session_id": session_id},
            recoverable=False,
        )


class FailureNotFoundError(ControlPlaneError):
    def __init__(self, failure_id: str):
        super().__init__(
            error_code=ToolErrorCode.FAILURE_NOT_FOUND,
            message=f"Failure record '{failure_id}' not found in platform telemetry.",
            details={"failure_id": failure_id},
            recoverable=False,
        )


class PredictionNotFoundError(ControlPlaneError):
    def __init__(self, identifier: str):
        super().__init__(
            error_code=ToolErrorCode.PREDICTION_NOT_FOUND,
            message=f"Reliability prediction for '{identifier}' could not be located.",
            details={"identifier": identifier},
            recoverable=True,
        )


class EvidenceNotFoundError(ControlPlaneError):
    def __init__(self, evidence_id: str):
        super().__init__(
            error_code=ToolErrorCode.EVIDENCE_NOT_FOUND,
            message=f"Evidence artifact '{evidence_id}' not found.",
            details={"evidence_id": evidence_id},
            recoverable=False,
        )


class InsufficientEvidenceError(ControlPlaneError):
    def __init__(self, application_id: str, count: int, required: int = 3):
        super().__init__(
            error_code=ToolErrorCode.INSUFFICIENT_EVIDENCE,
            message=f"Application '{application_id}' has only {count} observations; at least {required} required.",
            details={"application_id": application_id, "count": count, "required": required},
            recoverable=True,
        )


class ReliabilityAbstainedError(ControlPlaneError):
    def __init__(self, application_id: str, uncertainty: float, threshold: float):
        super().__init__(
            error_code=ToolErrorCode.RELIABILITY_ABSTAINED,
            message=f"Reliability decision engine abstained for '{application_id}': uncertainty ({uncertainty:.4f}) exceeds decision threshold ({threshold:.4f}).",
            details={"application_id": application_id, "uncertainty": uncertainty, "threshold": threshold},
            recoverable=True,
        )


class UnauthorizedActionError(ControlPlaneError):
    def __init__(self, tool_name: str, reason: str = "Agent role not permitted to invoke action tools without explicit token."):
        super().__init__(
            error_code=ToolErrorCode.UNAUTHORIZED_ACTION,
            message=f"Unauthorized invocation of action tool '{tool_name}': {reason}",
            details={"tool_name": tool_name},
            recoverable=False,
        )


class InvalidRequestError(ControlPlaneError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code=ToolErrorCode.INVALID_REQUEST,
            message=message,
            details=details or {},
            recoverable=True,
        )


class StaleEvidenceError(ControlPlaneError):
    def __init__(self, evidence_id: str, age_seconds: float):
        super().__init__(
            error_code=ToolErrorCode.STALE_EVIDENCE,
            message=f"Evidence '{evidence_id}' is stale ({age_seconds:.1f}s old) and cannot be reliably used for diagnosis.",
            details={"evidence_id": evidence_id, "age_seconds": age_seconds},
            recoverable=True,
        )


class InternalError(ControlPlaneError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code=ToolErrorCode.INTERNAL_ERROR,
            message=message,
            details=details or {},
            recoverable=False,
        )


class ResourceNotFoundError(ControlPlaneError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            error_code=ToolErrorCode.INVALID_REQUEST,
            message=message,
            details=details or {},
            recoverable=False,
        )

