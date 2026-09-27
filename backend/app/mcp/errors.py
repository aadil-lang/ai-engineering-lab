"""
MCP Error Translation Layer.
Converts domain/control-plane errors into machine-readable MCP responses
without leaking Python stack traces, credentials, or internal filesystem paths.
"""

from typing import Any
from backend.app.models.tools import ToolErrorCode, ToolError, ToolResponseEnvelope, ToolResponseMetadata, ToolProvenance
from backend.app.control_plane.errors import ControlPlaneError


def is_abstention_semantic_state(error_code: ToolErrorCode | str) -> bool:
    """
    Abstention is NOT an error in the Reliability Control Plane.
    Checks if an error code represents valid statistical abstention.
    """
    code_str = str(error_code.value if isinstance(error_code, ToolErrorCode) else error_code).upper()
    return code_str in ["RELIABILITY_ABSTAINED", "INSUFFICIENT_EVIDENCE"]


def format_mcp_error_payload(
    tool_name: str,
    error_code: ToolErrorCode | str,
    message: str,
    request_id: str = "mcp_req_err",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Creates a machine-readable, structured error dictionary suitable for JSON serialization in MCP.
    """
    code_str = error_code.value if isinstance(error_code, ToolErrorCode) else str(error_code)

    # Sanitize message to ensure zero tracebacks or filesystem paths escape
    safe_message = message.split("\n")[0].strip()
    if len(safe_message) > 250:
        safe_message = safe_message[:247] + "..."

    return {
        "success": False,
        "error": {
            "error_code": code_str,
            "message": safe_message,
            "details": details or {},
            "recoverable": code_str in [
                "INVALID_REQUEST",
                "INSUFFICIENT_EVIDENCE",
                "RELIABILITY_ABSTAINED",
                "UNAUTHORIZED_ACTION",
            ],
        },
        "metadata": {
            "tool_name": tool_name,
            "tool_version": "1.0",
            "request_id": request_id,
        },
    }
