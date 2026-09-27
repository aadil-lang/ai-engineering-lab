from typing import Any
from fastapi import APIRouter, HTTPException, Body, Header, Query
from pydantic import BaseModel

from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.control_plane.audit import AuditLogger
from backend.app.models.tools import ToolResponseEnvelope

router = APIRouter()

# Single shared instance of ReliabilityControlPlane
control_plane = ReliabilityControlPlane()


@router.get("", response_model=list[dict[str, Any]])
def list_capabilities() -> list[dict[str, Any]]:
    """
    Discovery endpoint: returns list of all registered tools and their capabilities.
    Transport-independent and ready for autonomous agent discovery.
    """
    return control_plane.registry.list_capabilities()


@router.get("/schemas/mcp", response_model=list[dict[str, Any]])
def get_mcp_schemas() -> list[dict[str, Any]]:
    """
    Returns all registered tools exported in MCP-compatible tool schema format.
    Zero MCP SDK dependency in core logic.
    """
    return [t.to_mcp_tool_schema() for t in control_plane.registry.list_tools()]


@router.get("/audit/recent", response_model=list[dict[str, Any]])
def get_recent_audit_events(limit: int = Query(default=50, ge=1, le=100)) -> list[dict[str, Any]]:
    """
    Returns recent cryptographic audit events for developer inspection and monitoring.
    """
    events = AuditLogger.get_recent_events(limit=limit)
    return [e.model_dump() for e in events]


@router.get("/{tool_name}", response_model=dict[str, Any])
def get_tool_definition(tool_name: str) -> dict[str, Any]:
    """
    Returns the metadata, description, input schema, and output schema for a specific tool.
    """
    tool = control_plane.registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found in registry.")

    return {
        "name": tool.name,
        "description": tool.description,
        "version": tool.version,
        "mode": tool.mode.value,
        "permission_mode": tool.permission_mode,
        "input_schema": tool.get_input_schema(),
        "output_schema": tool.get_output_schema(),
    }


@router.post("/{tool_name}/invoke", response_model=ToolResponseEnvelope[Any])
def invoke_tool(
    tool_name: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    x_request_id: str | None = Header(None, alias="X-Request-ID"),
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> ToolResponseEnvelope[Any]:
    """
    Executes a canonical reliability tool with full lifecycle validation,
    security redaction, and cryptographic audit recording.
    """
    tool = control_plane.registry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")

    ctx = ToolInvocationContext.create_default(
        session_id=x_session_id or payload.get("session_id"),
        idempotency_key=x_idempotency_key or payload.get("idempotency_key"),
        actor="rest_agent_adapter",
    )
    if x_request_id:
        ctx.request_id = x_request_id
    if authorization:
        ctx.auth_token = authorization

    try:
        request_obj = control_plane.registry.validate_request(tool_name, payload)
    except Exception as e:
        # Pass validation error through standard control plane error envelope
        return control_plane.registry.invoke(
            tool_name=tool_name,
            request_obj=tool.request_model(),  # fallback for metadata
            context=ctx,
        )

    return control_plane.registry.invoke(
        tool_name=tool_name,
        request_obj=request_obj,
        context=ctx,
    )
