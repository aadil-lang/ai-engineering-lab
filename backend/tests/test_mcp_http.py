import pytest
import httpx2
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server, create_streamable_http_app


@pytest.mark.anyio
async def test_mcp_streamable_http_transport_full_lifecycle():
    server, adapter = create_mcp_server()
    app = create_streamable_http_app(server, streamable_http_path="/mcp")

    transport = httpx2.ASGITransport(app=app)
    async with server.session_manager.run():
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as http_client:
            async with streamable_http_client("http://127.0.0.1/mcp", http_client=http_client) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    init_res = await client.initialize()
                    assert init_res.server_info.name == "Autonomous QA Reliability Server"

                    # 1. Discover all 10 tools over HTTP
                    tools_res = await client.list_tools()
                    assert len(tools_res.tools) == 10

                    # 2. Invoke inspect_application over HTTP
                    res1 = await client.call_tool("inspect_application", {"application_id": "app_inventory"})
                    assert res1.is_error is False
                    d1 = res1.structured_content
                    assert d1["success"] is True
                    assert d1["data"]["application_id"] == "app_inventory"

                    # 3. Invoke get_uncertainty over HTTP
                    res2 = await client.call_tool("get_uncertainty", {"application_id": "app_inventory"})
                    assert res2.is_error is False
                    d2 = res2.structured_content
                    assert d2["success"] is True
                    assert "uncertainty_width" in d2["data"]

                    # 4. Malformed input over HTTP produces structured error
                    res3 = await client.call_tool("start_test_session", {"invalid_param_xyz": 123})
                    assert res3.is_error is True
                    d3 = res3.structured_content
                    assert d3["success"] is False
                    assert d3["error"]["error_code"] == "INVALID_REQUEST"


@pytest.mark.anyio
async def test_cross_transport_equivalence_stdio_and_http():
    """
    Section 25: Cross-transport equivalence test.
    For the same logical request, the domain data payload must be identical
    across STDIO and Streamable HTTP.
    """
    server, adapter = create_mcp_server()
    app = create_streamable_http_app(server, streamable_http_path="/mcp")

    # 1. Execute via direct in-memory session (representing stdio engine)
    stdio_res = await adapter.call_tool(
        name="inspect_application",
        arguments={"application_id": "app_inventory"},
        transport="stdio",
    )
    stdio_data = stdio_res.structured_content["data"]

    # 2. Execute via Streamable HTTP
    transport = httpx2.ASGITransport(app=app)
    async with server.session_manager.run():
        async with httpx2.AsyncClient(transport=transport, base_url="http://127.0.0.1") as http_client:
            async with streamable_http_client("http://127.0.0.1/mcp", http_client=http_client) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as client:
                    await client.initialize()
                    http_res = await client.call_tool("inspect_application", {"application_id": "app_inventory"})
                    http_data = http_res.structured_content["data"]

    # 3. Verify domain payload equivalence
    assert stdio_data["application_id"] == http_data["application_id"]
    assert stdio_data["name"] == http_data["name"]
    assert stdio_data["base_url"] == http_data["base_url"]
    assert stdio_data["latest_reliability_state"] == http_data["latest_reliability_state"]
    assert stdio_data["total_runs"] == http_data["total_runs"]
    assert stdio_data["total_failures"] == http_data["total_failures"]
