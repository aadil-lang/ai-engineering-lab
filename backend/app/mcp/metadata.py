"""
MCP Server Metadata and Version Definitions for Slice 7.3.
"""

MCP_SERVER_NAME: str = "Autonomous QA Reliability Server"
MCP_SERVER_VERSION: str = "7.3.0"
MCP_TOOL_CONTRACT_VERSION: str = "reliability-tools/v1"
MCP_SDK_VERSION: str = "2.2.0"
MCP_PROTOCOL_VERSION: str = "2024-11-05"

SERVER_METADATA: dict[str, str] = {
    "name": MCP_SERVER_NAME,
    "version": MCP_SERVER_VERSION,
    "protocol": MCP_PROTOCOL_VERSION,
    "sdk_version": MCP_SDK_VERSION,
    "tool_contract": MCP_TOOL_CONTRACT_VERSION,
    "description": (
        "Model Context Protocol adapter for the Autonomous QA Reliability Platform. "
        "Provides 10 canonical reliability tools with cryptographic provenance, "
        "security redaction, and strict epistemic fact classification."
    ),
}
