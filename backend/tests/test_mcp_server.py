import pytest
import anyio
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server
from backend.app.mcp.metadata import MCP_SERVER_NAME, MCP_SERVER_VERSION


@pytest.mark.anyio
async def test_mcp_server_initialization_and_handshake():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            init_res = await client.initialize()
            assert init_res.server_info.name == MCP_SERVER_NAME
            assert init_res.server_info.version == MCP_SERVER_VERSION
            assert init_res.capabilities.tools is not None
        tg.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_server_list_tools_exact_ten_canonical_tools():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    expected_tools = {
        "inspect_application",
        "start_test_session",
        "get_application_health",
        "get_prediction",
        "get_uncertainty",
        "list_failures",
        "get_failure",
        "diagnose_failure",
        "get_evidence",
        "get_reliability_summary",
    }

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()
            tools_res = await client.list_tools()
            discovered = {t.name for t in tools_res.tools}

            assert len(tools_res.tools) == 10
            assert discovered == expected_tools

            # Verify every tool has non-empty description and valid JSON input schema
            for t in tools_res.tools:
                assert t.description is not None and len(t.description) > 0
                assert isinstance(t.input_schema, dict)
                assert t.input_schema.get("type") == "object"
        tg.cancel_scope.cancel()
