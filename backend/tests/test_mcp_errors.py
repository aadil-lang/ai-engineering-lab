import pytest
import anyio
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_unknown_tool_structured_error():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            res = await client.call_tool("nonexistent_tool_xyz", {})
            assert res.is_error is True
            payload = res.structured_content
            assert payload["success"] is False
            assert payload["error"]["error_code"] == "INVALID_REQUEST"
            # Ensure no traceback leaked
            assert "Traceback" not in payload["error"]["message"]

        tg.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_application_not_found_structured_error():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            res = await client.call_tool("inspect_application", {"application_id": "app_does_not_exist"})
            assert res.is_error is True
            payload = res.structured_content
            assert payload["success"] is False
            assert payload["error"]["error_code"] == "APPLICATION_NOT_FOUND"

        tg.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_abstention_is_not_an_error():
    """
    Critical Invariant:
    If the reliability platform abstains (e.g. UNKNOWN health state or low evidence),
    MCP must NOT convert it into an error or failure!
    """
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            # Uncertainty request for app with few local observations
            res = await client.call_tool("get_uncertainty", {"application_id": "app_booking"})
            assert res.is_error is False
            payload = res.structured_content
            assert payload["success"] is True
            assert "abstention_recommended" in payload["data"]

        tg.cancel_scope.cancel()
