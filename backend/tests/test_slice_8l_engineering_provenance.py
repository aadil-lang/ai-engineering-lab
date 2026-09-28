"""
Test Suite for Slice 8L: Unified Engineering Provenance & End-to-End Change Trace

Validates:
1. Canonical lifecycle event serialization and SHA-256 cryptographic chaining.
2. Append-only SQLite event store with monotonic sequence ordering.
3. Cryptographic chain verification & tamper detection (modifications, deletions, bad hashes).
4. Provenance service: Full lifecycle recording from REQUEST_CREATED to POST_CHANGE_VERIFICATION_COMPLETED.
5. End-to-end trace assembly and lifecycle completeness calculation.
6. Event correction modeling without mutating historical events.
7. ReliabilityControlPlane MCP tools (record_lifecycle_event, get_provenance_trace, verify_provenance_chain).
8. REST API endpoints (/api/v1/provenance/*).
"""

import os
import gc
import sqlite3
import tempfile
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.provenance.models import (
    ActorType,
    LifecycleEventType,
    EngineeringLifecycleEvent,
    ProvenanceChainVerificationResult,
    ProvenanceTrace,
)
from backend.app.provenance.hashing import (
    serialize_canonical_payload,
    calculate_event_hash,
    GENESIS_HASH,
)
from backend.app.provenance.repository import ProvenanceRepository
from backend.app.provenance.service import ProvenanceService
from backend.app.control_plane.service import ReliabilityControlPlane
from backend.app.main import app


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for isolated provenance testing."""
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
def repo(temp_db):
    """Instantiate a clean ProvenanceRepository."""
    return ProvenanceRepository(temp_db)


@pytest.fixture
def service(repo):
    """Instantiate a clean ProvenanceService."""
    return ProvenanceService(repo)


@pytest.fixture
def test_client(temp_db, monkeypatch):
    """FastAPI TestClient with isolated temporary provenance repository."""
    repo = ProvenanceRepository(temp_db)
    service = ProvenanceService(repo)
    from backend.app.api.v1 import provenance as prov_api
    monkeypatch.setattr(prov_api, "_provenance_service", service)
    return TestClient(app)


# =========================================================================
# 1. Cryptographic Hashing & Canonical Serialization Tests
# =========================================================================

def test_canonical_serialization_is_deterministic():
    """Ensure metadata ordering does not alter canonical serialization."""
    d1 = {"event_id": "evt-1", "metadata": {"b": 2, "a": 1, "nested": {"z": "end", "m": "middle"}}}
    d2 = {"event_id": "evt-1", "metadata": {"nested": {"m": "middle", "z": "end"}, "a": 1, "b": 2}}
    
    s1 = serialize_canonical_payload(d1)
    s2 = serialize_canonical_payload(d2)
    assert s1 == s2
    assert '"a":1' in s1


def test_event_hash_generation():
    """Verify SHA-256 hash generation is sensitive to payload and previous hash."""
    payload = {"event_id": "evt-1", "event_type": "REQUEST_CREATED"}
    h1 = calculate_event_hash(payload, GENESIS_HASH)
    assert len(h1) == 64
    
    # Different payload must yield different hash
    h2 = calculate_event_hash({"event_id": "evt-2", "event_type": "REQUEST_CREATED"}, GENESIS_HASH)
    assert h1 != h2
    
    # Same payload with different previous_hash must yield different hash
    h3 = calculate_event_hash(payload, "1" * 64)
    assert h1 != h3


# =========================================================================
# 2. Append-Only Repository & Cryptographic Chaining Tests
# =========================================================================

def test_genesis_event_chaining(repo):
    """The very first event in an empty store must link to GENESIS_HASH with sequence_number 1."""
    event = EngineeringLifecycleEvent(
        event_id="evt-genesis",
        event_type=LifecycleEventType.REQUEST_CREATED,
        actor_type=ActorType.HUMAN,
        actor_id="engineer-alice",
        correlation_id="corr-test-1",
        metadata={"title": "Fix prompt truncation bug"},
    )
    saved = repo.append_event(event)
    
    assert saved.sequence_number == 1
    assert saved.previous_event_hash == GENESIS_HASH
    assert len(saved.event_hash) == 64
    
    # Re-verify calculation
    computed = calculate_event_hash(saved.model_dump(), GENESIS_HASH)
    assert saved.event_hash == computed


def test_sequential_hash_chaining(repo):
    """Subsequent events must link to the immediately preceding event hash."""
    e1 = EngineeringLifecycleEvent(
        event_id="evt-001",
        event_type=LifecycleEventType.REQUEST_CREATED,
        actor_type=ActorType.HUMAN,
        correlation_id="corr-chain",
    )
    s1 = repo.append_event(e1)
    
    e2 = EngineeringLifecycleEvent(
        event_id="evt-002",
        event_type=LifecycleEventType.IMPLEMENTATION_STARTED,
        actor_type=ActorType.AI_AGENT,
        correlation_id="corr-chain",
    )
    s2 = repo.append_event(e2)
    
    assert s2.sequence_number == 2
    assert s2.previous_event_hash == s1.event_hash
    assert s2.event_hash != s1.event_hash
    
    verification = repo.verify_chain()
    assert verification.is_valid is True
    assert verification.verified_events == 2
    assert verification.violation_type is None


def test_tamper_detection_modified_payload(repo, temp_db):
    """Direct database modification of an event's payload must be detected."""
    e1 = EngineeringLifecycleEvent(
        event_id="evt-tamper-1",
        event_type=LifecycleEventType.REQUEST_CREATED,
        actor_type=ActorType.HUMAN,
        correlation_id="corr-tamper",
        metadata={"target": "legit"},
    )
    repo.append_event(e1)
    
    # Tamper with the row directly in SQLite (metadata_json column)
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "UPDATE engineering_lifecycle_events SET metadata_json = ? WHERE event_id = ?",
        ('{"target": "hacked"}', "evt-tamper-1")
    )
    conn.commit()
    conn.close()
    
    verification = repo.verify_chain()
    assert verification.is_valid is False
    assert verification.violation_type == "MODIFIED_EVENT"
    assert verification.broken_event_id == "evt-tamper-1"


def test_tamper_detection_broken_chain(repo, temp_db):
    """Direct modification of previous_event_hash must be detected as INCORRECT_PREVIOUS_HASH."""
    e1 = EngineeringLifecycleEvent(
        event_id="evt-tc-1",
        event_type=LifecycleEventType.REQUEST_CREATED,
        actor_type=ActorType.HUMAN,
        correlation_id="corr-break",
    )
    repo.append_event(e1)
    
    e2 = EngineeringLifecycleEvent(
        event_id="evt-tc-2",
        event_type=LifecycleEventType.IMPLEMENTATION_STARTED,
        actor_type=ActorType.AI_AGENT,
        correlation_id="corr-break",
    )
    repo.append_event(e2)
    
    # Tamper with e2's previous_event_hash
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "UPDATE engineering_lifecycle_events SET previous_event_hash = ? WHERE event_id = ?",
        ("f" * 64, "evt-tc-2")
    )
    conn.commit()
    conn.close()
    
    verification = repo.verify_chain()
    assert verification.is_valid is False
    assert verification.violation_type == "INCORRECT_PREVIOUS_HASH"
    assert verification.broken_event_id == "evt-tc-2"


def test_tamper_detection_deleted_event(repo, temp_db):
    """Direct deletion of an intermediate event creates a broken hash link."""
    e1 = repo.append_event(EngineeringLifecycleEvent(
        event_id="evt-del-1", event_type=LifecycleEventType.REQUEST_CREATED, actor_type=ActorType.HUMAN, correlation_id="corr-del"
    ))
    e2 = repo.append_event(EngineeringLifecycleEvent(
        event_id="evt-del-2", event_type=LifecycleEventType.IMPLEMENTATION_STARTED, actor_type=ActorType.HUMAN, correlation_id="corr-del"
    ))
    e3 = repo.append_event(EngineeringLifecycleEvent(
        event_id="evt-del-3", event_type=LifecycleEventType.IMPLEMENTATION_COMPLETED, actor_type=ActorType.HUMAN, correlation_id="corr-del"
    ))
    
    # Delete intermediate event 2
    conn = sqlite3.connect(temp_db)
    conn.execute("DELETE FROM engineering_lifecycle_events WHERE event_id = ?", ("evt-del-2",))
    conn.commit()
    conn.close()
    
    verification = repo.verify_chain()
    assert verification.is_valid is False
    # Event 3 expects e2's hash, but previous event in query is e1
    assert verification.broken_event_id == "evt-del-3"
    assert verification.violation_type == "INCORRECT_PREVIOUS_HASH"


# =========================================================================
# 3. Provenance Service & End-to-End Lifecycle Trace
# =========================================================================

def test_full_lifecycle_trace(service):
    """Simulate an entire end-to-end software change lifecycle and verify trace completeness."""
    cid = "corr-lifecycle-full"
    app_id = "question-generator-app"
    commit = "a1b2c3d4e5f67890"
    
    # 1. Request
    service.record_request(
        correlation_id=cid,
        title="Enhance token truncation handling",
        description="Add dynamic prompt sliding window",
        actor_id="eng-bob",
    )
    
    # 2. Commit
    service.record_commit(
        correlation_id=cid,
        git_commit=commit,
        message="Implement dynamic sliding window in generator",
        actor_id="eng-bob",
    )
    
    # 3. Pull Request
    service.record_pull_request(
        correlation_id=cid,
        pr_id="PR-42",
        title="Dynamic prompt sliding window",
        git_commit=commit,
    )
    
    # 4. AI Review
    service.record_ai_review(
        correlation_id=cid,
        pr_id="PR-42",
        decision="APPROVE",
        findings_count=0,
    )
    
    # 5. CI
    service.record_ci(
        correlation_id=cid,
        ci_run_id="ci-9988",
        status="SUCCESS",
        git_commit=commit,
    )
    
    # 6. Application Context
    service.record_application_context(
        correlation_id=cid,
        context_id="ctx-qgen-v2",
        application_id=app_id,
    )
    
    # 7. Change Impact
    service.record_change_impact(
        correlation_id=cid,
        change_set_id="cs-001",
        affected_count=2,
    )
    
    # 8. Regression Plan
    service.record_regression_plan(
        correlation_id=cid,
        plan_id="plan-reg-001",
        scope_summary={"targeted": 2, "smoke": 2},
    )
    
    # 9. Lab Execution
    service.record_lab_execution(
        correlation_id=cid,
        run_id="run-lab-401",
        target_id=app_id,
        status="COMPLETED",
    )
    
    # 10. Evidence
    service.record_evidence(
        correlation_id=cid,
        run_id="run-lab-401",
        evidence_id="ev-screen-901",
        evidence_type="DOM_SNAPSHOT",
    )
    
    # 11. AI Evaluation
    service.record_ai_evaluation(
        correlation_id=cid,
        run_id="run-lab-401",
        outcome="PASS",
    )
    
    # 12. Diagnosis
    service.record_diagnosis(
        correlation_id=cid,
        diagnosis_id="diag-clean-01",
        root_cause="NO_ANOMALY",
    )
    
    # 13. Remediation
    service.record_remediation(
        correlation_id=cid,
        remediation_id="rem-none-needed",
        status="NOT_APPLICABLE",
    )
    
    # 14. Governance Decision
    service.record_governance_decision(
        correlation_id=cid,
        governance_id="gov-rec-801",
        decision="APPROVE",
        actor_id="lead-engineer-charlie",
    )
    
    # 15. Change Authorized
    service.record_authorization(
        correlation_id=cid,
        authorization_id="auth-merge-801",
        scope="PRODUCTION_DEPLOY",
    )
    
    # 16. Independent Retest
    service.record_independent_retest(
        correlation_id=cid,
        run_id="retest-run-55",
        status="VERIFIED_GREEN",
    )
    
    # 17. Post-Change Verification
    service.record_post_change_verification(
        correlation_id=cid,
        application_id=app_id,
        verified=True,
    )
    
    # Retrieve trace
    trace = service.get_provenance_trace(cid)
    
    assert trace.correlation_id == cid
    assert trace.total_events == 17
    assert trace.is_complete_lifecycle is True
    assert len(trace.stages_present) >= 8
    
    # Verify chain
    chain_res = service.verify_chain()
    assert chain_res.is_valid is True
    assert chain_res.verified_events == 17


def test_event_correction_append_only(service):
    """Corrections are recorded as append-only EVENT_CORRECTION events, not modifying history."""
    e_original = service.record_request(
        correlation_id="corr-correction",
        title="Initial Request",
        description="Initial description",
        actor_id="user-1",
    )
    
    # Correction event
    e_corr = service.record_correction(
        correlation_id="corr-correction",
        target_event_id=e_original.event_id,
        rationale="Corrected typo in request description",
        details={"description": "Corrected description"},
    )
    
    assert e_corr.event_type == LifecycleEventType.EVENT_CORRECTION
    assert e_corr.parent_event_id == e_original.event_id
    assert e_corr.sequence_number == 2
    assert e_corr.previous_event_hash == e_original.event_hash
    
    # History intact
    events = service.repo.list_events(correlation_id="corr-correction")
    assert len(events) == 2
    assert events[0].event_id == e_original.event_id
    assert events[1].event_id == e_corr.event_id


# =========================================================================
# 4. Control Plane & MCP Tools Integration Tests
# =========================================================================

def test_control_plane_provenance_mcp_tools(temp_db):
    """Verify ReliabilityControlPlane exposes provenance MCP tools."""
    from backend.app.control_plane.context import ToolInvocationContext
    from backend.app.models.provenance_tools import (
        RecordLifecycleEventRequest,
        GetLifecycleEventRequest,
        GetProvenanceTraceRequest,
        VerifyProvenanceChainRequest,
    )

    cp = ReliabilityControlPlane(
        db_path=temp_db,
        enable_provenance_tools=True,
    )
    
    tools = cp.registry.list_tools()
    tool_names = [t.name for t in tools]
    assert "record_lifecycle_event" in tool_names
    assert "get_lifecycle_event" in tool_names
    assert "get_provenance_trace" in tool_names
    assert "verify_provenance_chain" in tool_names

    ctx = ToolInvocationContext(
        invocation_id="inv_test_provenance",
        agent_id="test-agent",
        session_id="sess_prov",
    )
    
    # 1. Execute record_lifecycle_event tool via registry
    res_record = cp.registry.invoke(
        "record_lifecycle_event",
        RecordLifecycleEventRequest(
            event_type=LifecycleEventType.REQUEST_CREATED,
            actor_type=ActorType.AI_AGENT,
            actor_id="test-agent",
            correlation_id="mcp-test-corr",
            metadata={"source": "mcp_runner"},
        ),
        ctx,
    )
    assert res_record.success is True
    assert res_record.data is not None
    event_id = res_record.data.event.event_id
    assert event_id.startswith("evt_prov_")
    assert res_record.data.event.sequence_number == 1
    
    # 2. Execute get_lifecycle_event tool via registry
    res_get = cp.registry.invoke(
        "get_lifecycle_event",
        GetLifecycleEventRequest(event_id=event_id),
        ctx,
    )
    assert res_get.success is True
    assert res_get.data is not None
    assert res_get.data.event is not None
    assert res_get.data.event.event_id == event_id
    
    # 3. Execute get_provenance_trace tool via registry
    res_trace = cp.registry.invoke(
        "get_provenance_trace",
        GetProvenanceTraceRequest(correlation_id="mcp-test-corr"),
        ctx,
    )
    assert res_trace.success is True
    assert res_trace.data is not None
    assert res_trace.data.trace.total_events == 1
    
    # 4. Execute verify_provenance_chain tool via registry
    res_verify = cp.registry.invoke(
        "verify_provenance_chain",
        VerifyProvenanceChainRequest(),
        ctx,
    )
    assert res_verify.success is True
    assert res_verify.data is not None
    assert res_verify.data.result.is_valid is True


# =========================================================================
# 5. REST API Integration Tests
# =========================================================================

def test_rest_api_provenance_flow(test_client):
    """Test REST API endpoints for event creation, query, trace, and verification."""
    # 1. Record event
    payload = {
        "event_type": "REQUEST_CREATED",
        "actor_type": "HUMAN",
        "actor_id": "api-tester",
        "correlation_id": "api-corr-001",
        "application_id": "demo-app",
        "git_commit": "789abc",
        "metadata": {"intent": "api integration test"},
    }
    resp = test_client.post("/api/v1/provenance/events", json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["event_id"].startswith("evt_prov_")
    assert created["sequence_number"] == 1
    assert created["previous_event_hash"] == GENESIS_HASH
    event_id = created["event_id"]
    
    # 2. Get by ID
    resp_get = test_client.get(f"/api/v1/provenance/events/{event_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["event_id"] == event_id
    
    # 3. Query events
    resp_query = test_client.get("/api/v1/provenance/events?correlation_id=api-corr-001")
    assert resp_query.status_code == 200
    query_data = resp_query.json()
    assert len(query_data) == 1
    assert query_data[0]["event_id"] == event_id
    
    # 4. Get Trace
    resp_trace = test_client.get("/api/v1/provenance/trace?correlation_id=api-corr-001")
    assert resp_trace.status_code == 200
    trace_data = resp_trace.json()
    assert trace_data["correlation_id"] == "api-corr-001"
    assert trace_data["total_events"] == 1
    
    # 5. Verify Chain
    resp_verify = test_client.post("/api/v1/provenance/verify")
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()
    assert verify_data["is_valid"] is True
    assert verify_data["verified_events"] == 1
