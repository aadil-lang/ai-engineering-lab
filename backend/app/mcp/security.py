"""
MCP Security Boundary.
Enforces strict external boundary rules:
- Zero raw shell / filesystem / database / Python execution exposure.
- Enforces ToolMode permissions (READ_ONLY vs ACTION).
- Asserts that responses are thoroughly redacted before reaching MCP clients.
"""

from typing import Any
from backend.app.models.tools import ToolMode, ToolErrorCode
from backend.app.control_plane.errors import UnauthorizedActionError, InvalidRequestError
from backend.app.control_plane.redaction import RedactionEngine

# Strictly disallowed capability names that an agent might try to invoke
FORBIDDEN_TOOL_PATTERNS = [
    "shell",
    "bash",
    "sh",
    "exec",
    "eval",
    "system",
    "sql",
    "query_db",
    "run_sql",
    "read_file",
    "write_file",
    "delete_file",
    "fs",
    "http_request",
    "fetch",
    "curl",
    "python",
    "run_code",
    "playwright_click",
    "playwright_type",
    "playwright_goto",
]


class MCPSecurityBoundary:
    """
    Guards MCP tool dispatch from unauthorized capabilities and malicious input patterns.
    """

    @staticmethod
    def validate_tool_request(tool_name: str, mode: ToolMode, permission_mode: str = "open") -> None:
        """
        Validates that the requested tool is legitimate and permitted under current security policy.
        """
        lower_name = tool_name.lower().strip()

        # Check for forbidden raw system capabilities
        for pattern in FORBIDDEN_TOOL_PATTERNS:
            if pattern in lower_name:
                raise UnauthorizedActionError(
                    f"Tool '{tool_name}' requests prohibited raw system access (pattern: {pattern}). "
                    "Only canonical reliability tools may be invoked via MCP."
                )

        # Enforce action permission mode if restricted
        if mode == ToolMode.ACTION and permission_mode == "restricted":
            raise UnauthorizedActionError(
                f"Tool '{tool_name}' requires ACTION privileges which are not authorized for this caller."
            )

    @staticmethod
    def sanitize_mcp_output(data: Any) -> tuple[Any, list[str]]:
        """
        Passes data through the RedactionEngine to ensure no Bearer tokens,
        JWTs, AWS keys, OpenAI keys, or credentials escape to the MCP client.
        """
        return RedactionEngine.redact_value(data)
