"""
MCP Tool Adapter for the Reliability Control Plane.
Acts as the single bridge between the canonical ToolRegistry and the MCP protocol.
Zero duplicate domain logic; zero contract drift.
"""

import logging
from typing import Any
import mcp.types as types
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.registry import ToolRegistry, ToolDefinition
from backend.app.models.tools import ToolErrorCode
from backend.app.mcp.context import build_mcp_invocation_context
from backend.app.mcp.security import MCPSecurityBoundary
from backend.app.mcp.serialization import (
    canonical_tool_to_mcp_tool,
    envelope_to_call_tool_result,
    error_to_call_tool_result,
)
from backend.app.control_plane.errors import ControlPlaneError, UnauthorizedActionError

logger = logging.getLogger("ai_qa_platform.mcp.adapter")


class MCPToolAdapter:
    """
    Adapter translating canonical Reliability Control Plane tools into MCP operations.
    Maintains a 1-to-1 dynamic mapping with the canonical ToolRegistry.
    """

    def __init__(self, control_plane: ReliabilityControlPlane | None = None):
        self.control_plane = control_plane or ReliabilityControlPlane()
        self.registry: ToolRegistry = self.control_plane.registry

    def get_mcp_tools(self) -> list[types.Tool]:
        """
        Dynamically derives all MCP tools from the canonical ToolRegistry.
        Does NOT maintain a second static list.
        """
        tool_defs = self.registry.list_tools()
        return [canonical_tool_to_mcp_tool(td) for td in tool_defs]

    def get_tool_definition(self, name: str) -> ToolDefinition | None:
        """Looks up a tool definition in the canonical registry."""
        return self.registry.get_tool(name)

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        transport: str = "stdio",
        actor: str = "mcp_agent",
    ) -> types.CallToolResult:
        """
        Executes a canonical tool request on behalf of an MCP client.
        Preserves complete envelope, provenance, audit trail, and security redaction.
        """
        args = arguments or {}
        ctx = build_mcp_invocation_context(
            arguments=args,
            actor=actor,
            transport=transport,
        )

        # 1. Lookup in canonical registry
        tool_def = self.registry.get_tool(name)
        if not tool_def:
            return error_to_call_tool_result(
                tool_name=name,
                error_code=ToolErrorCode.INVALID_REQUEST,
                message=f"Unknown tool '{name}'. Available tools: {[t.name for t in self.registry.list_tools()]}",
                request_id=ctx.request_id,
            )

        # 2. Security Boundary & Permission Validation
        try:
            MCPSecurityBoundary.validate_tool_request(
                tool_name=name,
                mode=tool_def.mode,
                permission_mode=tool_def.permission_mode,
            )
        except UnauthorizedActionError as uae:
            logger.warning(f"Unauthorized action blocked in MCP adapter: {uae}")
            return error_to_call_tool_result(
                tool_name=name,
                error_code=ToolErrorCode.UNAUTHORIZED_ACTION,
                message=str(uae),
                request_id=ctx.request_id,
            )
        except Exception as sec_err:
            logger.error(f"Security validation failure in MCP adapter: {sec_err}")
            return error_to_call_tool_result(
                tool_name=name,
                error_code=ToolErrorCode.UNAUTHORIZED_ACTION,
                message="Security validation failed for tool invocation.",
                request_id=ctx.request_id,
            )

        # 3. Request Validation
        try:
            request_obj = tool_def.request_model.model_validate(args)
        except Exception as val_err:
            logger.warning(f"Malformed input for tool '{name}': {val_err}")
            return error_to_call_tool_result(
                tool_name=name,
                error_code=ToolErrorCode.INVALID_REQUEST,
                message=f"Validation failed for tool '{name}': {val_err}",
                request_id=ctx.request_id,
            )

        # 4. Dispatch to Canonical Registry Invocation Lifecycle
        try:
            # The registry handles: execution handler, audit logging, redaction, envelope creation
            envelope = self.registry.invoke(
                tool_name=name,
                request_obj=request_obj,
                context=ctx,
            )
            return envelope_to_call_tool_result(envelope, tool_name=name)

        except Exception as exc:
            logger.exception(f"Unexpected error executing MCP tool '{name}': {exc}")
            return error_to_call_tool_result(
                tool_name=name,
                error_code=ToolErrorCode.INTERNAL_ERROR,
                message=f"Internal execution error in tool '{name}'",
                request_id=ctx.request_id,
            )
