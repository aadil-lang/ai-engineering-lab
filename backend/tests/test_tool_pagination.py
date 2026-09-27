import pytest
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.models.tools import ListFailuresRequest
from backend.app.control_plane.context import ToolInvocationContext


def test_list_failures_cursor_pagination():
    cp = ReliabilityControlPlane()
    ctx = ToolInvocationContext.create_default()

    # Request first page with limit=2
    req_page1 = ListFailuresRequest(application_id="app_inventory", limit=2)
    resp_page1 = cp.list_failures(req_page1, ctx)

    assert len(resp_page1.failures) <= 2
    if resp_page1.has_more:
        assert resp_page1.next_cursor is not None

        # Request second page using cursor
        req_page2 = ListFailuresRequest(
            application_id="app_inventory",
            limit=2,
            cursor=resp_page1.next_cursor,
        )
        resp_page2 = cp.list_failures(req_page2, ctx)

        # Ensure no overlapping items between page 1 and page 2
        page1_ids = {f.failure_id for f in resp_page1.failures}
        page2_ids = {f.failure_id for f in resp_page2.failures}
        assert page1_ids.isdisjoint(page2_ids)


def test_list_failures_severity_filtering():
    cp = ReliabilityControlPlane()
    ctx = ToolInvocationContext.create_default()

    req = ListFailuresRequest(severity="HIGH", limit=10)
    resp = cp.list_failures(req, ctx)
    for f in resp.failures:
        assert f.severity.upper() == "HIGH"
