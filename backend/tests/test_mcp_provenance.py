import pytest
import anyio
from mcp.client.session import ClientSession
from backend.app.mcp.server import create_mcp_server


@pytest.mark.anyio
async def test_mcp_preserves_prediction_provenance():
    server, adapter = create_mcp_server()

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            res = await client.call_tool("get_prediction", {"application_id": "app_inventory"})
            assert res.is_error is False
            payload = res.structured_content

            # Envelope metadata provenance
            prov = payload["metadata"]["provenance"]
            assert prov["snapshot_id"] == "eval_snap_slice_7_1"
            assert prov["model_version"] == "v1.1-scaled-logistic"
            assert prov["feature_schema_version"] == "v1.0-temporal"

            # Domain data provenance
            data = payload["data"]
            assert data["source_snapshot"] == "eval_snap_slice_7_1"
            assert data["model_version"] == "v1.1-scaled-logistic"
            assert data["feature_schema_version"] == "v1.0-temporal"
            assert isinstance(data["source_run_ids"], list)

        tg.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_preserves_epistemic_distinctions_in_diagnosis():
    server, adapter = create_mcp_server()

    failures = adapter.control_plane.repo.list_failures()
    if not failures:
        pytest.skip("No failures available in database for diagnosis test.")

    target_failure = failures[0]

    c2s_send, c2s_recv = anyio.create_memory_object_stream(10)
    s2c_send, s2c_recv = anyio.create_memory_object_stream(10)

    async with anyio.create_task_group() as tg:
        tg.start_soon(server.run, c2s_recv, s2c_send, server.create_initialization_options())
        async with ClientSession(s2c_recv, c2s_send) as client:
            await client.initialize()

            res = await client.call_tool("diagnose_failure", {"failure_id": target_failure.failure_id, "depth": "standard"})
            assert res.is_error is False
            diag_data = res.structured_content["data"]

            # Must contain distinct OBSERVED and INFERRED facts
            categories = {f["category"] for f in diag_data["supporting_evidence"] + diag_data["probable_root_causes"]}
            assert "OBSERVED" in categories
            assert "INFERRED" in categories
            # Epistemic separation invariant: Inferred causes must not be classified as OBSERVED
            for cause in diag_data["probable_root_causes"]:
                assert cause["category"] != "OBSERVED"

        tg.cancel_scope.cancel()
