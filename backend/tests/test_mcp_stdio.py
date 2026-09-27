import sys
import pytest
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


@pytest.mark.anyio
async def test_mcp_stdio_transport_end_to_end():
    params = StdioServerParameters(
        command=sys.executable,
        args=["scripts/run_mcp_server.py"],
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as client:
            init_res = await client.initialize()
            assert init_res.server_info.name == "Autonomous QA Reliability Server"

            # 1. Discover all 10 tools
            tools_res = await client.list_tools()
            assert len(tools_res.tools) == 10

            # 2. Invoke inspect_application
            call_res = await client.call_tool(
                "inspect_application",
                {"application_id": "app_inventory"},
            )
            assert call_res.is_error is False
            structured = call_res.structured_content
            assert structured["success"] is True
            assert structured["data"]["application_id"] == "app_inventory"

            # 3. Invoke get_application_health
            health_res = await client.call_tool(
                "get_application_health",
                {"application_id": "app_inventory"},
            )
            assert health_res.is_error is False
            assert health_res.structured_content["data"]["health_state"] in [
                "HEALTHY", "DEGRADED", "UNRELIABLE", "UNKNOWN"
            ]

            # 4. Unknown tool error over STDIO
            bad_res = await client.call_tool("unknown_tool_stdio", {})
            assert bad_res.is_error is True
            assert bad_res.structured_content["error"]["error_code"] == "INVALID_REQUEST"
