import pytest
import anyio
import json
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_invoke_read_only_tools_full_suite():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            # 1. inspect_application
            resp1 = await client.call_tool("inspect_application", {"application_id": "app_inventory"})
            assert resp1.is_error is False
            d1 = resp1.structured_content
            assert d1["success"] is True
            assert d1["data"]["application_id"] == "app_inventory"
            assert "known_capabilities" in d1["data"]

            # 2. get_application_health
            resp2 = await client.call_tool("get_application_health", {"application_id": "app_inventory"})
            assert resp2.is_error is False
            d2 = resp2.structured_content
            assert d2["success"] is True
            assert d2["data"]["health_state"] in ["HEALTHY", "DEGRADED", "UNRELIABLE", "UNKNOWN"]

            # 3. get_prediction
            resp3 = await client.call_tool("get_prediction", {"application_id": "app_inventory"})
            assert resp3.is_error is False
            d3 = resp3.structured_content
            assert d3["success"] is True
            assert 0.0 <= d3["data"]["probability"] <= 1.0
            assert d3["data"]["model_version"] == "v1.1-scaled-logistic"

            # 4. get_uncertainty
            resp4 = await client.call_tool("get_uncertainty", {"application_id": "app_inventory"})
            assert resp4.is_error is False
            d4 = resp4.structured_content
            assert d4["success"] is True
            assert d4["data"]["uncertainty_width"] >= 0.0
            assert "abstention_recommended" in d4["data"]

            # 5. list_failures
            resp5 = await client.call_tool("list_failures", {"application_id": "app_inventory", "limit": 5})
            assert resp5.is_error is False
            d5 = resp5.structured_content
            assert d5["success"] is True
            assert isinstance(d5["data"]["failures"], list)

            # 6. get_reliability_summary
            resp6 = await client.call_tool("get_reliability_summary", {"application_id": "app_eda"})
            assert resp6.is_error is False
            d6 = resp6.structured_content
            assert d6["success"] is True
            assert len(d6["data"]["top_risks"]) > 0

        tg.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_invoke_action_start_test_session():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            # Execute start_test_session action
            resp = await client.call_tool(
                "start_test_session",
                {
                    "application_id": "app_inventory",
                    "mode": "reliability",
                    "max_duration_seconds": 180,
                    "idempotency_key": "mcp_key_test_01",
                },
            )
            assert resp.is_error is False
            payload = resp.structured_content
            assert payload["success"] is True
            assert payload["data"]["application_id"] == "app_inventory"
            assert payload["data"]["status"] == "ACTIVE"
            assert payload["data"]["is_idempotent_replay"] is False

        tg.cancel_scope.cancel()
