"""
MCP Serialization Layer.
Converts canonical ToolDefinition instances to official mcp.types.Tool objects,
and maps canonical ToolResponseEnvelope instances to mcp.types.CallToolResult.
"""

import json
from typing import Any
import mcp.types as types
from backend.app.control_plane.registry import ToolDefinition
from backend.app.models.tools import ToolResponseEnvelope, ToolErrorCode
from backend.app.mcp.errors import is_abstention_semantic_state, format_mcp_error_payload
from backend.app.mcp.security import MCPSecurityBoundary


def canonical_tool_to_mcp_tool(tool_def: ToolDefinition) -> types.Tool:
    """
    Derives an official mcp.types.Tool directly from the canonical ToolDefinition.
    The canonical registry remains the single source of truth.
    """
    input_schema = tool_def.request_model.model_json_schema()
    envelope_model = ToolResponseEnvelope[tool_def.response_model]
    output_schema = envelope_model.model_json_schema()

    meta = {
        "mode": tool_def.mode.value,
        "version": tool_def.version,
        "permission_mode": tool_def.permission_mode,
        "contract": "reliability-tools/v1",
        "inner_response_schema": tool_def.response_model.model_json_schema(),
    }

    return types.Tool(
        name=tool_def.name,
        description=tool_def.description,
        input_schema=input_schema,
        output_schema=output_schema,
        meta=meta,
    )


def envelope_to_call_tool_result(
    envelope: ToolResponseEnvelope,
    tool_name: str,
) -> types.CallToolResult:
    """
    Translates a canonical ToolResponseEnvelope into an official mcp.types.CallToolResult.
    Preserves:
    - data payload (unflattened, with epistemic facts preserved)
    - complete metadata and cryptographic provenance
    - error structure if failed
    - abstention state (never treated as an error)
    """
    raw_dict = envelope.model_dump()
    sanitized_dict, _ = MCPSecurityBoundary.sanitize_mcp_output(raw_dict)

    # Determine is_error flag:
    # Abstention (e.g. INSUFFICIENT_EVIDENCE, RELIABILITY_ABSTAINED) is a valid scientific state, NOT an error!
    is_error = False
    if not envelope.success:
        err = envelope.error
        if err and is_abstention_semantic_state(err.error_code):
            is_error = False
        else:
            is_error = True

    # JSON text content for text-based MCP clients
    json_text = json.dumps(sanitized_dict, indent=2, default=str)

    content_blocks: list[types.ContentBlock] = [
        types.TextContent(
            type="text",
            text=json_text,
        )
    ]

    return types.CallToolResult(
        content=content_blocks,
        structured_content=sanitized_dict,
        is_error=is_error,
        result_type="complete",
        meta={
            "tool_name": tool_name,
            "request_id": envelope.metadata.request_id,
            "tool_version": envelope.metadata.tool_version,
            "execution_time_ms": envelope.metadata.execution_time_ms,
        },
    )


def error_to_call_tool_result(
    tool_name: str,
    error_code: ToolErrorCode | str,
    message: str,
    request_id: str = "mcp_err",
    details: dict[str, Any] | None = None,
) -> types.CallToolResult:
    """
    Translates an unhandled or adapter-level error into a structured CallToolResult.
    """
    payload = format_mcp_error_payload(
        tool_name=tool_name,
        error_code=error_code,
        message=message,
        request_id=request_id,
        details=details,
    )
    sanitized_payload, _ = MCPSecurityBoundary.sanitize_mcp_output(payload)
    is_err = not is_abstention_semantic_state(error_code)

    json_text = json.dumps(sanitized_payload, indent=2, default=str)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json_text)],
        structured_content=sanitized_payload,
        is_error=is_err,
        result_type="complete",
        meta={
            "tool_name": tool_name,
            "request_id": request_id,
            "error_code": str(error_code),
        },
    )
