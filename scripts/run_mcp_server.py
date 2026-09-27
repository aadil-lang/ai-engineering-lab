"""
CLI Entrypoint for running the Autonomous QA Reliability MCP Server.
Usage:
    python scripts/run_mcp_server.py                      # Starts STDIO transport (default)
    python scripts/run_mcp_server.py --transport http     # Starts Streamable HTTP transport
    python scripts/run_mcp_server.py --info               # Displays registered tools and metadata
"""

import sys
import os
import argparse
import asyncio
import logging

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.mcp.server import create_mcp_server, run_stdio_server, create_streamable_http_app
from backend.app.mcp.metadata import SERVER_METADATA, MCP_SERVER_NAME, MCP_SERVER_VERSION


def main():
    parser = argparse.ArgumentParser(description="Reliability MCP Server Runner")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol to run (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8005,
        help="HTTP port when running with --transport http (default: 8005)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="HTTP host when running with --transport http (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print server capabilities, versions, and exit",
    )

    args = parser.parse_args()

    server, adapter = create_mcp_server()

    if args.info:
        tools = adapter.get_mcp_tools()
        print("=" * 60)
        print(f" {MCP_SERVER_NAME} v{MCP_SERVER_VERSION}")
        print("=" * 60)
        print(f"Protocol Version: {SERVER_METADATA['protocol']}")
        print(f"Tool Contract:    {SERVER_METADATA['tool_contract']}")
        print(f"Total Tools:      {len(tools)}")
        print("\nRegistered Tools:")
        for t in tools:
            mode = t.meta.get("mode", "UNKNOWN") if t.meta else "UNKNOWN"
            print(f"  • {t.name:<25} [{mode:<9}] {t.description[:50]}...")
        print("=" * 60)
        return

    if args.transport == "stdio":
        # Run STDIO loop
        asyncio.run(run_stdio_server(server))
    elif args.transport == "http":
        import uvicorn
        logging.basicConfig(level=logging.INFO)
        app = create_streamable_http_app(server, streamable_http_path="/mcp")
        print(f"Starting {MCP_SERVER_NAME} on http://{args.host}:{args.port}/mcp ...")
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
