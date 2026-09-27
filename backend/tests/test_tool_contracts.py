import pytest
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.control_plane.errors import (
    ApplicationNotFoundError,
    FailureNotFoundError,
    EvidenceNotFoundError,
)
from backend.app.models.tools import (
    InspectApplicationRequest,
    StartTestSessionRequest,
    GetApplicationHealthRequest,
    GetPredictionRequest,
    GetUncertaintyRequest,
    ListFailuresRequest,
    GetFailureRequest,
    DiagnoseFailureRequest,
    GetEvidenceRequest,
    GetReliabilitySummaryRequest,
    SessionMode,
    DiagnosisDepth,
)


@pytest.fixture
def control_plane():
    return ReliabilityControlPlane()


@pytest.fixture
def context():
    return ToolInvocationContext.create_default()


def test_tool_inspect_application(control_plane, context):
    req = InspectApplicationRequest(application_id="app_inventory")
    resp = control_plane.inspect_application(req, context)
    assert resp.application_id == "app_inventory"
    assert resp.base_url != ""
    assert resp.known_capabilities != []


def test_tool_inspect_application_not_found(control_plane, context):
    req = InspectApplicationRequest(application_id="app_nonexistent")
    with pytest.raises(ApplicationNotFoundError):
        control_plane.inspect_application(req, context)


def test_tool_get_application_health(control_plane, context):
    req = GetApplicationHealthRequest(application_id="app_inventory")
    resp = control_plane.get_application_health(req, context)
    assert resp.application_id == "app_inventory"
    assert resp.health_state in ["HEALTHY", "DEGRADED", "UNRELIABLE", "UNKNOWN"]
    assert resp.failure_probability is not None


def test_tool_get_prediction(control_plane, context):
    req = GetPredictionRequest(application_id="app_inventory")
    resp = control_plane.get_prediction(req, context)
    assert resp.application_id == "app_inventory"
    assert 0.0 <= resp.probability <= 1.0
    assert resp.model_version == "v1.1-scaled-logistic"


def test_tool_get_uncertainty(control_plane, context):
    req = GetUncertaintyRequest(application_id="app_inventory")
    resp = control_plane.get_uncertainty(req, context)
    assert resp.application_id == "app_inventory"
    assert 0.0 <= resp.lower_bound <= resp.upper_bound <= 1.0
    assert resp.uncertainty_width >= 0.0


def test_tool_diagnose_failure_distinguishes_observed_inferred_hypothesized(control_plane, context):
    failures = control_plane.repo.list_failures()
    if not failures:
        pytest.skip("No natural failures present in database.")

    target_failure = failures[0]
    req = DiagnoseFailureRequest(failure_id=target_failure.failure_id, depth=DiagnosisDepth.standard)
    resp = control_plane.diagnose_failure(req, context)

    assert resp.failure_id == target_failure.failure_id
    # Ensure distinction between OBSERVED facts and INFERRED root causes
    categories = {fact.category.value for fact in resp.supporting_evidence + resp.probable_root_causes}
    assert "OBSERVED" in categories
    assert "INFERRED" in categories


def test_tool_get_evidence(control_plane, context):
    evidence_list = control_plane.repo.list_evidence()
    if not evidence_list:
        pytest.skip("No evidence artifacts in database.")

    target_ev = evidence_list[0]
    req = GetEvidenceRequest(evidence_id=target_ev.evidence_id)
    resp = control_plane.get_evidence(req, context)

    assert resp.evidence_id == target_ev.evidence_id
    assert len(resp.sha256_hash) == 64


def test_tool_get_reliability_summary(control_plane, context):
    req = GetReliabilitySummaryRequest(application_id="app_eda")
    resp = control_plane.get_reliability_summary(req, context)
    assert resp.application_id == "app_eda"
    assert resp.top_risks != []
    assert resp.recommended_next_actions != []
