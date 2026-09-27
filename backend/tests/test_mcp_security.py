import pytest
import anyio
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server
from backend.app.mcp.security import MCPSecurityBoundary
from backend.app.control_plane.errors import UnauthorizedActionError


def test_mcp_security_boundary_rejects_prohibited_tools():
    prohibited_tools = [
        "shell_exec",
        "bash_command",
        "run_sql",
        "read_file",
        "write_file",
        "http_request",
        "python_eval",
        "playwright_click",
    ]

    for tool_name in prohibited_tools:
        with pytest.raises(UnauthorizedActionError):
            MCPSecurityBoundary.validate_tool_request(
                tool_name=tool_name,
                mode=None,  # type: ignore
            )


@pytest.mark.anyio
async def test_mcp_output_redaction_guarantee():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            # Retrieve failure details which contains execution telemetry and stack trace
            failures_res = await client.call_tool("list_failures", {"limit": 1})
            failures = failures_res.structured_content["data"]["failures"]

            if failures:
                target_fid = failures[0]["failure_id"]
                detail_res = await client.call_tool("get_failure", {"failure_id": target_fid})
                text_output = detail_res.content[0].text

                # Assert that common secret patterns never leak in MCP text
                assert "Bearer eyJ" not in text_output
                assert "AKIAIOSFODNN7EXAMPLE" not in text_output
                assert "sk-proj-" not in text_output
                assert "BEGIN RSA PRIVATE KEY" not in text_output

        tg.cancel_scope.cancel()
