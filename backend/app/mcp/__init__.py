"""
MCP Adapter Package for Autonomous QA Reliability Platform.
Exposes the canonical Reliability Tool Registry through the Model Context Protocol (MCP).
"""

from backend.app.mcp.metadata import (
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
    MCP_TOOL_CONTRACT_VERSION,
    MCP_SDK_VERSION,
    MCP_PROTOCOL_VERSION,
    SERVER_METADATA,
)
from backend.app.mcp.adapter import MCPToolAdapter
from backend.app.mcp.server import create_mcp_server, create_streamable_http_app, run_stdio_server

__all__ = [
    "MCP_SERVER_NAME",
    "MCP_SERVER_VERSION",
    "MCP_TOOL_CONTRACT_VERSION",
    "MCP_SDK_VERSION",
    "MCP_PROTOCOL_VERSION",
    "SERVER_METADATA",
    "MCPToolAdapter",
    "create_mcp_server",
    "create_streamable_http_app",
    "run_stdio_server",
]
