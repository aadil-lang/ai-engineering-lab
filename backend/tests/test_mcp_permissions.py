import pytest
import anyio
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_action_idempotency_deduplication():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            idem_key = "mcp_idempotent_key_perm_test_99"

            # Call 1: New session
            res1 = await client.call_tool(
                "start_test_session",
                {
                    "application_id": "app_inventory",
                    "mode": "reliability",
                    "max_duration_seconds": 120,
                    "idempotency_key": idem_key,
                },
            )
            data1 = res1.structured_content["data"]
            session_id_1 = data1["session_id"]
            assert data1["is_idempotent_replay"] is False

            # Call 2: Exact same idempotency key
            res2 = await client.call_tool(
                "start_test_session",
                {
                    "application_id": "app_inventory",
                    "mode": "reliability",
                    "max_duration_seconds": 120,
                    "idempotency_key": idem_key,
                },
            )
            data2 = res2.structured_content["data"]
            session_id_2 = data2["session_id"]

            # Guarantees: Same logical session, is_idempotent_replay is True
            assert session_id_1 == session_id_2
            assert data2["is_idempotent_replay"] is True

        tg.cancel_scope.cancel()
