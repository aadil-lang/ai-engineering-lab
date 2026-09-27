import pytest
from pydantic import BaseModel
from backend.app.models.tools import ToolMode
from backend.app.control_plane.registry import ToolRegistry, ToolDefinition
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.control_plane.errors import InvalidRequestError, UnauthorizedActionError


class DummyRequest(BaseModel):
    app_id: str
    count: int = 1


class DummyResponse(BaseModel):
    result: str


def test_registry_registration_and_lookup():
    reg = ToolRegistry()

    def dummy_handler(req: DummyRequest, ctx: ToolInvocationContext):
        return DummyResponse(result=f"processed {req.app_id}")

    tool = ToolDefinition(
        name="test_tool",
        description="A test tool description",
        mode=ToolMode.READ_ONLY,
        request_model=DummyRequest,
        response_model=DummyResponse,
        handler=dummy_handler,
        version="1.0",
    )

    reg.register_tool(tool)
    assert reg.get_tool("test_tool") is not None
    assert reg.get_tool("unknown_tool") is None
    assert len(reg.list_tools()) == 1


def test_capability_discovery():
    reg = ToolRegistry()
    tool = ToolDefinition(
        name="inspect_app",
        description="Inspect app",
        mode=ToolMode.READ_ONLY,
        request_model=DummyRequest,
        response_model=DummyResponse,
        handler=lambda r, c: DummyResponse(result="ok"),
        version="1.0",
    )
    reg.register_tool(tool)

    caps = reg.list_capabilities()
    assert len(caps) == 1
    assert caps[0]["name"] == "inspect_app"
    assert caps[0]["version"] == "1.0"
    assert caps[0]["mode"] == "READ_ONLY"


def test_mcp_readiness_without_mcp_sdk():
    """
    Validates that every tool can export an MCP-compatible JSON schema definition
    without requiring or importing any MCP SDK packages.
    """
    tool = ToolDefinition(
        name="mcp_ready_tool",
        description="Checks MCP readiness",
        mode=ToolMode.READ_ONLY,
        request_model=DummyRequest,
        response_model=DummyResponse,
        handler=lambda r, c: DummyResponse(result="ok"),
        version="1.0",
    )

    mcp_schema = tool.to_mcp_tool_schema()
    assert mcp_schema["name"] == "mcp_ready_tool"
    assert "inputSchema" in mcp_schema
    assert "properties" in mcp_schema["inputSchema"]
    assert "app_id" in mcp_schema["inputSchema"]["properties"]
    assert mcp_schema["read_or_action"] == "READ_ONLY"


def test_request_validation():
    reg = ToolRegistry()
    tool = ToolDefinition(
        name="val_tool",
        description="Validate",
        mode=ToolMode.READ_ONLY,
        request_model=DummyRequest,
        response_model=DummyResponse,
        handler=lambda r, c: DummyResponse(result="ok"),
    )
    reg.register_tool(tool)

    # Valid request
    valid_req = reg.validate_request("val_tool", {"app_id": "test_app", "count": 5})
    assert isinstance(valid_req, DummyRequest)
    assert valid_req.app_id == "test_app"

    # Invalid request (missing required field)
    with pytest.raises(InvalidRequestError):
        reg.validate_request("val_tool", {"count": 5})


def test_action_tool_permission_mode():
    reg = ToolRegistry()
    tool = ToolDefinition(
        name="action_tool",
        description="Action test",
        mode=ToolMode.ACTION,
        request_model=DummyRequest,
        response_model=DummyResponse,
        handler=lambda r, c: DummyResponse(result="action_done"),
        permission_mode="restricted",
    )
    reg.register_tool(tool)

    ctx_no_auth = ToolInvocationContext.create_default()
    env_unauth = reg.invoke("action_tool", DummyRequest(app_id="test"), ctx_no_auth)
    assert not env_unauth.success
    assert env_unauth.error.error_code.value == "UNAUTHORIZED_ACTION"

    ctx_auth = ToolInvocationContext.create_default()
    ctx_auth.auth_token = "valid_token"
    env_auth = reg.invoke("action_tool", DummyRequest(app_id="test"), ctx_auth)
    assert env_auth.success
    assert env_auth.data.result == "action_done"
