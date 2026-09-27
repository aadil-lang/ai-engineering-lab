"""
MCP Invocation Context Helper.
Translates incoming MCP client parameters into a canonical ToolInvocationContext.
"""

import uuid
from typing import Any
from backend.app.control_plane.context import ToolInvocationContext


def build_mcp_invocation_context(
    arguments: dict[str, Any] | None = None,
    actor: str = "mcp_agent",
    transport: str = "stdio",
    session_id: str | None = None,
    auth_token: str | None = None,
) -> ToolInvocationContext:
    """
    Constructs a canonical ToolInvocationContext for an MCP tool invocation.
    Extracts session_id and idempotency_key from arguments if present.
    """
    args = arguments or {}
    sess_id = session_id or args.get("session_id")
    idempotency_key = args.get("idempotency_key")
    request_id = f"mcp_{uuid.uuid4().hex[:12]}"

    return ToolInvocationContext(
        request_id=request_id,
        actor=actor,
        session_id=sess_id,
        idempotency_key=idempotency_key,
        auth_token=auth_token,
    )
