import os
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.models.governance_tools import (
    ListRecommendationsRequest,
    CreateApprovalRequestRequest,
    GetApprovalRequestRequest,
    ApproveChangeRequest,
    RejectChangeRequest,
    GetChangeAuthorizationRequest,
    RevokeChangeAuthorizationRequest,
    GetGovernanceEvidenceRequest,
    GetGovernanceAuditRequest,
)
from backend.app.governance.models import (
    RecommendationType,
    RiskLevel,
    ApprovalRequestStatus,
    AuthorizationStatus,
)


@pytest.fixture
def control_plane_with_gov(tmp_path):
    db_file = str(tmp_path / "test_ctrl_gov.db")
    cp = ReliabilityControlPlane(
        db_path=db_file,
        enable_governance_tools=True,
    )
    return cp


def test_governance_tools_in_registry(control_plane_with_gov):
    cp = control_plane_with_gov
    tool_names = [t.name for t in cp.registry.list_tools()]

    # Tool count should now include the 10 governance tools
    assert "list_recommendations" in tool_names
    assert "get_recommendation" in tool_names
    assert "create_approval_request" in tool_names
    assert "get_approval_request" in tool_names
    assert "approve_change" in tool_names
    assert "reject_change" in tool_names
    assert "get_change_authorization" in tool_names
    assert "revoke_change_authorization" in tool_names
    assert "get_governance_evidence" in tool_names
    assert "get_governance_audit" in tool_names


def test_control_plane_governance_workflow(control_plane_with_gov):
    cp = control_plane_with_gov
    ctx = ToolInvocationContext()

    # 1. Create Evidence Package directly via service
    evidence_pkg = cp.governance_evidence_service.create_evidence_package(
        subject_type="PROMPT",
        subject_id="summarizer",
        prompt_version="2",
        evaluation_snapshot_id="snap_sum_02",
        observations=["Regression tests: 0 failures"],
    )

    # 2. Tool: create_approval_request
    req_dto = CreateApprovalRequestRequest(
        change_type=RecommendationType.PROMPT_CHANGE,
        subject_type="PROMPT",
        subject_id="summarizer",
        evidence_package_id=evidence_pkg.package_id,
        proposed_version="2",
        evaluation_snapshot_id="snap_sum_02",
    )
    apr_resp = cp.create_approval_request(req_dto, ctx)
    assert apr_resp.approval_request.approval_request_id.startswith("APR-")

    # 3. Tool: get_approval_request
    get_resp = cp.get_approval_request(
        GetApprovalRequestRequest(approval_request_id=apr_resp.approval_request.approval_request_id),
        ctx,
    )
    assert get_resp.approval_request.status == ApprovalRequestStatus.PENDING

    # 4. Tool: approve_change
    appr_resp = cp.approve_change(
        ApproveChangeRequest(
            approval_request_id=apr_resp.approval_request.approval_request_id,
            decision_maker_id="eng_evaluator@company.org",
            decision_reason="Evaluation snapshot verified",
            evidence_acknowledged=True,
            version_acknowledged=True,
            authorization_scope="PROMOTE",
        ),
        ctx,
    )
    assert appr_resp.approval_request.status == ApprovalRequestStatus.APPROVED
    assert appr_resp.authorization.status == AuthorizationStatus.ACTIVE

    # 5. Tool: get_change_authorization
    auth_resp = cp.get_change_authorization(
        GetChangeAuthorizationRequest(authorization_id=appr_resp.authorization.authorization_id),
        ctx,
    )
    assert auth_resp.authorization.authorized_version == "2"

    # 6. Tool: revoke_change_authorization
    rev_resp = cp.revoke_change_authorization(
        RevokeChangeAuthorizationRequest(
            authorization_id=appr_resp.authorization.authorization_id,
            actor_id="security_lead@company.org",
            revocation_reason="New vulnerability identified",
        ),
        ctx,
    )
    assert rev_resp.authorization.status == AuthorizationStatus.REVOKED

    # 7. Tool: get_governance_audit
    audit_resp = cp.get_governance_audit(
        GetGovernanceAuditRequest(subject_id="summarizer"),
        ctx,
    )
    assert len(audit_resp.audit_records) >= 3


def test_fastapi_governance_endpoints():
    client = TestClient(app)

    # 1. List recommendations
    res = client.get("/api/v1/governance/recommendations")
    assert res.status_code == 200

    # 2. Reject unauthenticated decision attempt
    res_no_auth = client.post(
        "/api/v1/governance/approval-requests/APR-TEST/approve",
        json={"decision_reason": "testing"},
    )
    assert res_no_auth.status_code == 401

    # 3. Reject AI agent identity
    res_ai = client.post(
        "/api/v1/governance/approval-requests/APR-TEST/approve",
        headers={"X-Human-User": "agent-gpt-4"},
        json={"decision_reason": "AI approving"},
    )
    assert res_ai.status_code == 403
