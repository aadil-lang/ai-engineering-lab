import pytest
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.models.tools import (
    InspectApplicationRequest,
    ToolMode,
    ToolErrorCode,
)


def test_control_plane_initialization_and_registry():
    cp = ReliabilityControlPlane()
    assert len(cp.registry.list_tools()) == 10
    caps = cp.registry.list_capabilities()
    assert len(caps) == 10


def test_control_plane_invocation_lifecycle_success():
    cp = ReliabilityControlPlane()
    ctx = ToolInvocationContext.create_default()

    req = InspectApplicationRequest(application_id="app_inventory")
    env = cp.registry.invoke("inspect_application", req, ctx)

    assert env.success is True
    assert env.data.application_id == "app_inventory"
    assert env.error is None
    assert env.metadata.tool_name == "inspect_application"
    assert env.metadata.execution_time_ms >= 0.0
    assert env.metadata.provenance.snapshot_id == "eval_snap_slice_7_1"


def test_control_plane_error_envelope_conversion():
    cp = ReliabilityControlPlane()
    ctx = ToolInvocationContext.create_default()

    req = InspectApplicationRequest(application_id="app_does_not_exist")
    env = cp.registry.invoke("inspect_application", req, ctx)

    assert env.success is False
    assert env.data is None
    assert env.error is not None
    assert env.error.error_code == ToolErrorCode.APPLICATION_NOT_FOUND
    assert "not found" in env.error.message.lower()
