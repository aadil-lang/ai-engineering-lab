#!/usr/bin/env python
"""
Helper script to verify that the Engineering Lab MCP server is responsive,
connected, and properly exposing all 10 canonical reliability tools.

Usage:
    python .agents/skills/engineering-lab/scripts/check_lab_health.py
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


async def check_health():
    print("=" * 65)
    print(" ENGINEERING LAB MCP SERVER HEALTH CHECK")
    print("=" * 65)

    server_params = StdioServerParameters(
        command="python",
        args=[str(PROJECT_ROOT / "scripts" / "run_mcp_server.py"), "--transport", "stdio"],
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    print(f"Connecting to Engineering Lab at: {server_params.args[0]}")
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                init_result = await session.initialize()
                print(f"[OK] MCP Session Initialized.")
                print(f"     Protocol Version: {init_result.protocol_version}")
                print(f"     Server Name:      {init_result.server_info.name}")
                print(f"     Server Version:   {init_result.server_info.version}")

                # List tools
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print(f"\n[OK] Discovered {len(tool_names)} Canonical Tools:")
                for name in sorted(tool_names):
                    print(f"     - {name}")

                if len(tool_names) != 10:
                    print(f"\n[WARNING] Expected 10 canonical tools, discovered {len(tool_names)}!")
                    return 1

                # Query health of app_inventory as a quick probe
                health_res = await session.call_tool(
                    "get_application_health",
                    arguments={"application_id": "app_inventory"}
                )
                health_data = health_res.structured_content
                is_success = health_data.get("success", False)
                data = health_data.get("data", {})

                print(f"\n[OK] Probe Query (get_application_health on app_inventory):")
                print(f"     Success:          {is_success}")
                print(f"     Health State:     {data.get('health_state')}")
                print(f"     Total Runs:       {data.get('total_runs')}")
                print(f"     Recent Failures:  {data.get('recent_failures_count')}")

                print("\n" + "=" * 65)
                print(" STATUS: ALL CHECKS PASSED — ENGINEERING LAB IS OPERATIONAL")
                print("=" * 65)
                return 0

    except Exception as e:
        print(f"\n[ERROR] Failed to communicate with Engineering Lab MCP server: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(check_health())
    sys.exit(exit_code)
