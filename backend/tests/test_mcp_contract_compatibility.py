import pytest
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.mcp.adapter import MCPToolAdapter


def test_mcp_contract_compatibility_and_schema_equivalence():
    cp = ReliabilityControlPlane()
    adapter = MCPToolAdapter(control_plane=cp)

    canonical_tools = cp.registry.list_tools()
    mcp_tools = adapter.get_mcp_tools()

    assert len(canonical_tools) == 10
    assert len(mcp_tools) == 10

    mcp_tool_map = {t.name: t for t in mcp_tools}

    for canonical in canonical_tools:
        assert canonical.name in mcp_tool_map, f"Missing MCP tool: {canonical.name}"
        mcp_tool = mcp_tool_map[canonical.name]

        # 1. Names and descriptions match
        assert mcp_tool.name == canonical.name
        assert mcp_tool.description == canonical.description

        # 2. Permission mode metadata preserved
        assert mcp_tool.meta is not None
        assert mcp_tool.meta["mode"] == canonical.mode.value
        assert mcp_tool.meta["version"] == canonical.version
        assert mcp_tool.meta["permission_mode"] == canonical.permission_mode

        # 3. Input Schema Equivalence:
        # Canonical Pydantic JSON schema must equal the MCP input schema
        canonical_input_schema = canonical.request_model.model_json_schema()
        assert mcp_tool.input_schema == canonical_input_schema, (
            f"Input schema drift detected for tool '{canonical.name}'"
        )

        # 4. Output & Envelope Schema Equivalence
        from backend.app.models.tools import ToolResponseEnvelope
        canonical_envelope_schema = ToolResponseEnvelope[canonical.response_model].model_json_schema()
        assert mcp_tool.output_schema == canonical_envelope_schema, (
            f"Envelope output schema drift detected for tool '{canonical.name}'"
        )
        assert mcp_tool.meta["inner_response_schema"] == canonical.response_model.model_json_schema(), (
            f"Inner data response schema drift detected for tool '{canonical.name}'"
        )


def test_no_extra_or_undocumented_mcp_tools():
    cp = ReliabilityControlPlane()
    adapter = MCPToolAdapter(control_plane=cp)

    canonical_names = {t.name for t in cp.registry.list_tools()}
    mcp_names = {t.name for t in adapter.get_mcp_tools()}

    # Exactly identical sets - no phantom MCP tools allowed
    assert canonical_names == mcp_names
