"""
MCP Server Initialization and Transport Binding.
Provides lowlevel MCP Server instance dynamically wired to the canonical ToolRegistry.
Supports both STDIO and Streamable HTTP transports.
"""

import sys
import logging
from typing import Any
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from starlette.applications import Starlette

from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.mcp.metadata import MCP_SERVER_NAME, MCP_SERVER_VERSION
from backend.app.mcp.adapter import MCPToolAdapter

logger = logging.getLogger("ai_qa_platform.mcp.server")


def create_mcp_server(
    control_plane: ReliabilityControlPlane | None = None,
    adapter: MCPToolAdapter | None = None,
) -> tuple[Server, MCPToolAdapter]:
    """
    Factory function creating an MCP Server hooked into the canonical ToolRegistry.
    Guarantees that all 10 canonical tools are dynamically registered.
    """
    tool_adapter = adapter or MCPToolAdapter(control_plane=control_plane)

    server = Server(
        name=MCP_SERVER_NAME,
        version=MCP_SERVER_VERSION,
    )

    # 1. Register tools/list handler
    async def handle_list_tools(
        context: Any,
        params: types.PaginatedRequestParams | None = None,
    ) -> types.ListToolsResult:
        logger.info("MCP client requested tools/list")
        mcp_tools = tool_adapter.get_mcp_tools()
        return types.ListToolsResult(tools=mcp_tools)

    server.add_request_handler("tools/list", types.PaginatedRequestParams, handle_list_tools)

    # 2. Register tools/call handler
    async def handle_call_tool(
        context: Any,
        params: types.CallToolRequestParams,
    ) -> types.CallToolResult:
        logger.info(f"MCP client executing tool '{params.name}'")
        return await tool_adapter.call_tool(
            name=params.name,
            arguments=params.arguments or {},
            transport="mcp",
        )

    server.add_request_handler("tools/call", types.CallToolRequestParams, handle_call_tool)

    return server, tool_adapter


def create_streamable_http_app(
    server: Server,
    streamable_http_path: str = "/",
    stateless_http: bool = True,
    json_response: bool = True,
    enable_dns_rebinding_protection: bool = False,
) -> Starlette:
    """
    Generates a Starlette ASGI application exposing Streamable HTTP for MCP clients.
    Can be mounted directly under FastAPI or run as an independent service.
    """
    from mcp.server.transport_security import TransportSecuritySettings

    sec = TransportSecuritySettings(
        enable_dns_rebinding_protection=enable_dns_rebinding_protection,
        allowed_hosts=["*"],
    )

    return server.streamable_http_app(
        streamable_http_path=streamable_http_path,
        stateless_http=stateless_http,
        json_response=json_response,
        transport_security=sec,
    )


async def run_stdio_server(server: Server) -> None:
    """
    Runs the MCP server over STDIO (standard input/output).
    Critical: Redirects standard Python logging to sys.stderr so that
    stdout is reserved exclusively for JSON-RPC messages.
    """
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="[MCP-STDIO %(levelname)s] %(asctime)s - %(message)s",
    )
    logger.info(f"Starting {MCP_SERVER_NAME} v{MCP_SERVER_VERSION} on STDIO...")

    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(
            read_stream=read_stream,
            write_stream=write_stream,
            initialization_options=init_options,
            raise_exceptions=False,
        )
