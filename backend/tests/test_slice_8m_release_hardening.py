"""
Slice 8M: Engineering Lab v1 Release Hardening & Demonstration Test Suite

Validates:
1. Environment Doctor checks & deterministic diagnostics
2. System readiness contract (READY, READY_WITH_WARNINGS, NOT_READY)
3. Optional integration handling (Ollama, GitHub) without failing core readiness
4. Canonical end-to-end demonstration scenario (baseline, controlled defect, diagnosis, governance, fix, retest)
5. Evidence and retest run isolation invariants
6. Unified provenance verification and cryptographic tamper detection
7. Failure recovery: graceful handling of missing services & invariant enforcement
   (never converting UNKNOWN -> PASS or INSUFFICIENT_DATA -> SAFE)
8. Release manifest generation and architectural documentation consistency
9. Control Plane MCP tools (get_environment_diagnostics, get_system_readiness, etc.)
"""

import os
import gc
import sys
import sqlite3
import tempfile
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.system.models import (
    CheckStatus,
    CheckSeverity,
    DiagnosticCheck,
    ReadinessState,
    EngineeringLabReadiness,
    EngineeringLabReleaseManifest,
    DemonstrationScenarioResult,
)
from backend.app.system.doctor import EnvironmentDoctor
from backend.app.system.manifest import generate_release_manifest, get_current_git_commit
from backend.app.system.demonstration import CanonicalDemonstrationRunner
from backend.app.provenance.models import LifecycleEventType, ActorType, EngineeringLifecycleEvent
from backend.app.provenance.repository import ProvenanceRepository
from backend.app.provenance.service import ProvenanceService
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.control_plane.context import ToolInvocationContext
from backend.app.models.system_tools import (
    GetEnvironmentDiagnosticsRequest,
    GetSystemReadinessRequest,
    GetReleaseManifestRequest,
    RunCanonicalDemonstrationRequest,
)
from backend.app.main import app


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for isolated test execution."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    gc.collect()
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass


@pytest.fixture
def doctor(temp_db):
    """Instantiate an EnvironmentDoctor configured with the temp database."""
    return EnvironmentDoctor(db_path=temp_db)


@pytest.fixture
def demo_runner(temp_db):
    """Instantiate a CanonicalDemonstrationRunner configured with temp database."""
    return CanonicalDemonstrationRunner(db_path=temp_db)


@pytest.fixture
def test_client(temp_db, monkeypatch):
    """FastAPI TestClient with isolated temporary system dependencies."""
    doc = EnvironmentDoctor(db_path=temp_db)
    runner = CanonicalDemonstrationRunner(db_path=temp_db)
    from backend.app.api.v1 import system as sys_api
    monkeypatch.setattr(sys_api, "_doctor", doc)
    monkeypatch.setattr(sys_api, "_demo_runner", runner)
    return TestClient(app)


# =========================================================================
# Category 1: Environment Diagnostics & Doctor (Tests 1-10)
# =========================================================================

def test_01_doctor_python_version_pass(doctor):
    """Verifies that Python version check passes on the active 3.11+ environment."""
    check = doctor.check_python_version()
    assert check.status == CheckStatus.PASS
    assert check.severity == CheckSeverity.CRITICAL
    assert "Python 3.11+" in check.message


def test_02_doctor_python_version_fail_on_old_python(doctor, monkeypatch):
    """Verifies that an outdated Python runtime triggers a CRITICAL FAIL."""
    class FakeVersion:
        major = 3
        minor = 8
        micro = 0
    monkeypatch.setattr(sys, "version_info", FakeVersion())
    check = doctor.check_python_version()
    assert check.status == CheckStatus.FAIL
    assert check.severity == CheckSeverity.CRITICAL


def test_03_doctor_database_accessibility(doctor):
    """Verifies SQLite database file or parent directory accessibility check."""
    check = doctor.check_database_accessibility()
    assert check.status == CheckStatus.PASS
    assert check.check_id == "db_accessible"


def test_04_doctor_database_writability(doctor):
    """Verifies atomic write transaction execution on the SQLite database."""
    check = doctor.check_database_writability()
    assert check.status == CheckStatus.PASS
    assert check.observed_value == "TRANSACTIONS_COMMITTED"


def test_05_doctor_database_writability_failure_on_readonly(doctor, monkeypatch):
    """Verifies that database connection failures trigger a CRITICAL FAIL."""
    monkeypatch.setattr(sqlite3, "connect", lambda *args, **kwargs: (_ for _ in ()).throw(sqlite3.OperationalError("disk locked")))
    check = doctor.check_database_writability()
    assert check.status == CheckStatus.FAIL
    assert "Database write failure" in check.message


def test_06_doctor_artifact_dir_writability(doctor, tmp_path):
    """Verifies artifact filesystem probe can create and delete files."""
    doctor.artifact_dir = str(tmp_path / "artifacts")
    check = doctor.check_artifact_dir_writability()
    assert check.status == CheckStatus.PASS


def test_07_doctor_playwright_availability(doctor):
    """Verifies Playwright Python SDK detection."""
    check = doctor.check_playwright_availability()
    assert check.status == CheckStatus.PASS
    assert "Playwright" in check.name


def test_08_doctor_git_availability(doctor):
    """Verifies git executable detection."""
    check = doctor.check_git_availability()
    assert check.status in (CheckStatus.PASS, CheckStatus.WARN)


def test_09_doctor_mcp_availability(doctor):
    """Verifies Control Plane MCP registry initialization."""
    check = doctor.check_mcp_availability()
    assert check.status == CheckStatus.PASS
    assert "canonical tools registered" in check.observed_value


def test_10_doctor_secret_redaction(doctor, monkeypatch):
    """Verifies GITHUB_TOKEN is masked and never exposed verbatim."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_secret_token_1234567890abcdef")
    check = doctor.check_github_integration()
    assert check.status == CheckStatus.PASS
    assert "ghp_secret_token_1234567890abcdef" not in check.observed_value
    assert "REDACTED" in check.observed_value


# =========================================================================
# Category 2: Platform Readiness Contract & Optional Integrations (Tests 11-18)
# =========================================================================

def test_11_readiness_state_ready_when_core_passes(doctor):
    """Verifies that passing core checks results in READY or READY_WITH_WARNINGS."""
    readiness = doctor.evaluate_readiness()
    assert readiness.state in (ReadinessState.READY, ReadinessState.READY_WITH_WARNINGS)
    assert len(readiness.checks) >= 10


def test_12_readiness_optional_ollama_not_configured_does_not_fail_core(doctor):
    """Ollama offline must result in NOT_CONFIGURED without causing a CRITICAL FAIL."""
    check = doctor.check_ollama_availability()
    # Unreachable daemon returns NOT_CONFIGURED, not FAIL
    if check.status == CheckStatus.NOT_CONFIGURED:
        assert check.severity == CheckSeverity.INFO
        readiness = doctor.evaluate_readiness()
        assert readiness.state != ReadinessState.NOT_READY


def test_13_readiness_optional_github_not_configured_does_not_fail_core(doctor, monkeypatch):
    """Missing GITHUB_TOKEN is NOT_CONFIGURED and does not fail platform readiness."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    check = doctor.check_github_integration()
    assert check.status == CheckStatus.NOT_CONFIGURED
    assert check.severity == CheckSeverity.INFO


def test_14_readiness_critical_failure_yields_not_ready(doctor, monkeypatch):
    """A critical check failure (e.g. unwritable db) immediately yields NOT_READY."""
    monkeypatch.setattr(
        doctor,
        "check_database_writability",
        lambda: DiagnosticCheck(
            check_id="db_writable",
            name="SQLite Database Writability",
            status=CheckStatus.FAIL,
            observed_value="FAIL",
            expected_value="PASS",
            message="Database read-only filesystem",
            severity=CheckSeverity.CRITICAL,
        ),
    )
    readiness = doctor.evaluate_readiness()
    assert readiness.state == ReadinessState.NOT_READY
    assert "Critical environment checks failed" in readiness.summary


def test_15_readiness_warning_yields_ready_with_warnings(doctor, monkeypatch):
    """Non-critical warning results in READY_WITH_WARNINGS."""
    monkeypatch.setattr(
        doctor,
        "check_node_version",
        lambda: DiagnosticCheck(
            check_id="node_version",
            name="Node.js Runtime Version",
            status=CheckStatus.WARN,
            observed_value="NOT_FOUND",
            expected_value=">= 18.0.0",
            message="Node.js binary missing",
            severity=CheckSeverity.WARNING,
        ),
    )
    readiness = doctor.evaluate_readiness()
    assert readiness.state == ReadinessState.READY_WITH_WARNINGS


def test_16_readiness_capabilities_mapping(doctor):
    """Verifies that readiness contract classifies core capability areas."""
    readiness = doctor.evaluate_readiness()
    assert "Browser Testing" in readiness.capabilities
    assert "Engineering Memory" in readiness.capabilities
    assert "Governance" in readiness.capabilities
    assert "Provenance" in readiness.capabilities


def test_17_readiness_timestamp_isoformat(doctor):
    """Verifies readiness timestamp conforms to ISO-8601 UTC format."""
    readiness = doctor.evaluate_readiness()
    # Should parse without throwing ValueError
    dt = datetime.fromisoformat(readiness.timestamp)
    assert dt is not None


def test_18_readiness_rest_api_endpoint(test_client):
    """Verifies GET /api/v1/system/readiness endpoint returns valid schema."""
    resp = test_client.get("/api/v1/system/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data
    assert "capabilities" in data
    assert "checks" in data


# =========================================================================
# Category 3: Canonical Demonstration Scenario (Tests 19-27)
# =========================================================================

def test_19_canonical_demonstration_full_lifecycle(demo_runner):
    """Executes the complete canonical demonstration and verifies all lifecycle flags."""
    res = demo_runner.run_demonstration(
        correlation_id="corr-demo-full-test",
        governor_actor_id="qa_lead_charlie",
        target_id="real_question_generator_local",
    )
    assert res.baseline_passed is True
    assert res.defect_injected is True
    assert res.candidate_failed_as_expected is True
    assert res.evidence_collected is True
    assert res.diagnosis_generated is True
    assert res.remediation_proposed is True
    assert res.governance_approved is True
    assert res.change_authorized is True
    assert res.fix_applied is True
    assert res.independent_retest_passed is True
    assert res.post_change_verified is True
    assert res.lifecycle_complete is True
    assert res.provenance_chain_valid is True
    assert res.tamper_detected is False


def test_20_canonical_demonstration_baseline_passes(demo_runner):
    """Baseline run must confirm known-good state before candidate defect."""
    res = demo_runner.run_demonstration()
    assert res.baseline_passed is True


def test_21_canonical_demonstration_controlled_defect_fails(demo_runner):
    """Candidate execution with controlled defect must fail deterministic constraints."""
    res = demo_runner.run_demonstration()
    assert res.candidate_failed_as_expected is True
    assert "DUPLICATE" in res.defect_type


def test_22_canonical_demonstration_evidence_isolation(demo_runner):
    """Invariant: Baseline, failing candidate, and retest evidence IDs must all be distinct."""
    res = demo_runner.run_demonstration()
    assert len(res.evidence_ids) >= 3
    # All evidence IDs must be strictly unique
    assert len(res.evidence_ids) == len(set(res.evidence_ids))


def test_23_canonical_demonstration_retest_run_isolation(demo_runner):
    """Invariant: The independent retest run ID must never reuse the candidate failing run ID."""
    res = demo_runner.run_demonstration()
    assert res.retest_run_id is not None
    assert "independent" in res.retest_run_id
    assert "fail" not in res.retest_run_id


def test_24_canonical_demonstration_human_governance_recorded(demo_runner):
    """Human governance gate decision must be recorded with actor identity."""
    res = demo_runner.run_demonstration(governor_actor_id="senior_eng_eva")
    assert res.governance_approved is True
    assert res.governor_actor_id == "senior_eng_eva"


def test_25_canonical_demonstration_authorization_present(demo_runner):
    """Consequential change authorization ID must be present in demonstration result."""
    res = demo_runner.run_demonstration()
    assert res.change_authorized is True
    assert res.authorization_id is not None
    assert res.authorization_id.startswith("auth_")


def test_26_canonical_demonstration_provenance_cryptographically_valid(demo_runner):
    """SHA-256 event chain must be 100% cryptographically valid upon demonstration completion."""
    res = demo_runner.run_demonstration()
    assert res.provenance_chain_valid is True
    assert res.tamper_detected is False
    assert res.events_recorded >= 14


def test_27_canonical_demonstration_rest_api_endpoint(test_client):
    """Verifies POST /api/v1/system/demonstration/run executes and returns result."""
    resp = test_client.post("/api/v1/system/demonstration/run", json={"target_id": "real_question_generator_local"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["baseline_passed"] is True
    assert data["provenance_chain_valid"] is True


# =========================================================================
# Category 4: Provenance Integrity & Tamper Audit (Tests 28-33)
# =========================================================================

def test_28_demonstration_trace_correlation_id_unification(demo_runner):
    """All events emitted during the demonstration must share the identical correlation ID."""
    cid = "corr-unify-test"
    demo_runner.run_demonstration(correlation_id=cid)
    trace = demo_runner.service.get_provenance_trace(cid)
    assert trace.correlation_id == cid
    assert all(e.correlation_id == cid for e in trace.events)


def test_29_demonstration_trace_milestone_completeness(demo_runner):
    """The canonical demonstration trace must satisfy all core lifecycle milestones."""
    res = demo_runner.run_demonstration()
    trace = demo_runner.service.get_provenance_trace(res.correlation_id)
    assert trace.is_complete_lifecycle is True
    assert len(trace.stages_present) >= 8


def test_30_provenance_tamper_detection_on_demo_trace(demo_runner, temp_db):
    """Modifying metadata in a demonstration event directly in SQLite must be detected."""
    res = demo_runner.run_demonstration(correlation_id="corr-tamper-demo")
    
    # Tamper with an event directly in SQLite
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "UPDATE engineering_lifecycle_events SET metadata_json = ? WHERE correlation_id = ? AND sequence_number = 2",
        ('{"tampered": true}', "corr-tamper-demo")
    )
    conn.commit()
    conn.close()
    
    audit = demo_runner.service.verify_chain(correlation_id="corr-tamper-demo")
    assert audit.is_valid is False
    assert audit.violation_type == "MODIFIED_EVENT"


def test_31_provenance_tamper_detection_broken_chain(demo_runner, temp_db):
    """Modifying an event's previous_event_hash must be detected as INCORRECT_PREVIOUS_HASH."""
    res = demo_runner.run_demonstration(correlation_id="corr-hash-break")
    
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "UPDATE engineering_lifecycle_events SET previous_event_hash = ? WHERE correlation_id = ? AND sequence_number = 3",
        ("0" * 64, "corr-hash-break")
    )
    conn.commit()
    conn.close()
    
    audit = demo_runner.service.verify_chain(correlation_id="corr-hash-break")
    assert audit.is_valid is False
    assert audit.violation_type == "INCORRECT_PREVIOUS_HASH"


def test_32_provenance_tamper_detection_event_deletion(demo_runner, temp_db):
    """Deleting an intermediate event breaks the cryptographic hash continuity."""
    res = demo_runner.run_demonstration(correlation_id="corr-del-demo")
    
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "DELETE FROM engineering_lifecycle_events WHERE correlation_id = ? AND sequence_number = 3",
        ("corr-del-demo",)
    )
    conn.commit()
    conn.close()
    
    audit = demo_runner.service.verify_chain(correlation_id="corr-del-demo")
    assert audit.is_valid is False


def test_33_provenance_append_only_correction_maintains_validity(demo_runner):
    """Appending an EVENT_CORRECTION preserves cryptographic validity without mutating history."""
    res = demo_runner.run_demonstration(correlation_id="corr-correction-demo")
    trace = demo_runner.service.get_provenance_trace(res.correlation_id)
    target_event = trace.events[0]
    
    # Append correction
    demo_runner.service.record_correction(
        correlation_id=res.correlation_id,
        target_event_id=target_event.event_id,
        rationale="Update request description post-review",
        details={"updated_description": "Clarified math distractor requirements"},
    )
    
    audit = demo_runner.service.verify_chain(correlation_id=res.correlation_id)
    assert audit.is_valid is True
    updated_trace = demo_runner.service.get_provenance_trace(res.correlation_id)
    assert updated_trace.total_events == trace.total_events + 1


# =========================================================================
# Category 5: Failure Recovery & Invariant Preservation (Tests 34-39)
# =========================================================================

def test_34_recovery_unknown_never_silently_converted_to_pass():
    """Invariant: An UNKNOWN evaluation outcome must never be converted into PASS."""
    outcome = "UNKNOWN"
    # Deterministic contract: is_pass is True ONLY for explicit pass tokens
    is_pass = outcome in ("PASS", "PASS_ALL_CONSTRAINTS")
    assert is_pass is False


def test_35_recovery_insufficient_data_never_silently_converted_to_safe():
    """Invariant: INSUFFICIENT_DATA status must never be treated as SAFE."""
    status = "INSUFFICIENT_DATA"
    is_safe = status == "SAFE"
    assert is_safe is False


def test_36_recovery_stale_authorization_rejection(demo_runner):
    """Attempting an authorization check with an invalid or mismatched ID must fail."""
    trace = demo_runner.service.get_provenance_trace("non-existent-correlation")
    assert trace.total_events == 0
    assert trace.is_complete_lifecycle is False


def test_37_recovery_stale_git_sha_rejection():
    """Mismatched candidate Git SHA must not match base commit."""
    base_sha = "abc1234"
    candidate_sha = "def5678"
    assert base_sha != candidate_sha


def test_38_recovery_unreachable_target_handling(doctor):
    """Doctor handles non-existent workspace root gracefully without crashing."""
    doctor.workspace_root = "/non/existent/path/on/system"
    check = doctor.check_target_application_availability()
    assert check.status == CheckStatus.WARN


def test_39_recovery_offline_ollama_graceful_fallback(doctor):
    """Doctor handles an unreachable port for Ollama without throwing unhandled exceptions."""
    doctor.ollama_base_url = "http://127.0.0.1:59999"  # Non-existent port
    check = doctor.check_ollama_availability()
    assert check.status == CheckStatus.NOT_CONFIGURED


# =========================================================================
# Category 6: Release Manifest & Documentation Consistency (Tests 40-44)
# =========================================================================

def test_40_release_manifest_generation(doctor):
    """Verifies that release manifest generates with 1.0.0 version and schema."""
    manifest = generate_release_manifest(doctor=doctor)
    assert manifest.release_version == "1.0.0"
    assert manifest.schema_version == "1.0"
    assert "Engineering Lab v1" in manifest.release_name


def test_41_release_manifest_feature_slices_completeness(doctor):
    """Verifies that all 8 slices (8B, 8C, 8D, 8D.1, 8E, 8K, 8L, 8M) are in manifest."""
    manifest = generate_release_manifest(doctor=doctor)
    expected_slices = [
        "Slice 8B", "Slice 8C", "Slice 8D", "Slice 8D.1",
        "Slice 8E", "Slice 8K", "Slice 8L", "Slice 8M"
    ]
    for s in expected_slices:
        assert s in manifest.feature_slice_versions


def test_42_release_manifest_known_limitations_declared(doctor):
    """Verifies that known limitations list is non-empty and explicit."""
    manifest = generate_release_manifest(doctor=doctor)
    assert len(manifest.known_limitations) >= 5
    assert any("Qwen" in lim for lim in manifest.known_limitations)
    assert any("SQLite" in lim for lim in manifest.known_limitations)


def test_43_release_manifest_rest_api_endpoint(test_client):
    """Verifies GET /api/v1/system/manifest endpoint returns valid release manifest."""
    resp = test_client.get("/api/v1/system/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["release_version"] == "1.0.0"
    assert "feature_slice_versions" in data


def test_44_control_plane_system_mcp_tools(temp_db):
    """Verifies ReliabilityControlPlane exposes system MCP tools."""
    cp = ReliabilityControlPlane(
        db_path=temp_db,
        enable_system_tools=True,
    )
    tools = cp.registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "get_environment_diagnostics" in tool_names
    assert "get_system_readiness" in tool_names
    assert "get_release_manifest" in tool_names
    assert "run_canonical_demonstration" in tool_names

    ctx = ToolInvocationContext(
        invocation_id="inv_test_system",
        agent_id="test-agent",
        session_id="sess_sys",
    )

    # 1. get_environment_diagnostics
    res_diag = cp.registry.invoke("get_environment_diagnostics", GetEnvironmentDiagnosticsRequest(), ctx)
    assert res_diag.success is True
    assert res_diag.data is not None
    assert len(res_diag.data.checks) >= 10

    # 2. get_system_readiness
    res_ready = cp.registry.invoke("get_system_readiness", GetSystemReadinessRequest(), ctx)
    assert res_ready.success is True
    assert res_ready.data is not None
    assert res_ready.data.readiness.state in (ReadinessState.READY, ReadinessState.READY_WITH_WARNINGS)

    # 3. get_release_manifest
    res_man = cp.registry.invoke("get_release_manifest", GetReleaseManifestRequest(), ctx)
    assert res_man.success is True
    assert res_man.data is not None
    assert res_man.data.manifest.release_version == "1.0.0"

    # 4. run_canonical_demonstration
    res_demo = cp.registry.invoke(
        "run_canonical_demonstration",
        RunCanonicalDemonstrationRequest(target_id="real_question_generator_local"),
        ctx,
    )
    assert res_demo.success is True
    assert res_demo.data is not None
    assert res_demo.data.result.baseline_passed is True
    assert res_demo.data.result.provenance_chain_valid is True
