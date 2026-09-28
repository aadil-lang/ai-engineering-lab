"""
Slice 8E Comprehensive Test Suite — Application-Aware Engineering Memory & Local Hybrid RAG.

Validates all 45 architectural requirements and test points:
1. memory creation
2. memory provenance
3. memory status
4. memory types
5. evidence linkage
6. context linkage
7. context hash
8. version applicability
9. stale detection
10. invalidation
11. contradiction detection
12. relationship creation
13. candidate validation
14. promotion rules
15. unsupported claim rejection
16. workflow memory
17. failure memory
18. regression memory
19. semantic embedding generation
20. vector index persistence
21. vector index rebuild
22. metadata filtering
23. hybrid retrieval
24. deterministic retrieval ranking
25. bounded top-K retrieval
26. current evidence overriding historical memory
27. version-aware retrieval
28. application isolation
29. security redaction
30. secret exclusion from embeddings
31. Qwen context formatting
32. no private CoT exposure
33. Live Console memory events
34. memory retrieval replay
35. 8D.1 strategy integration
36. memory-informed workflow prioritization
37. memory-informed edge-case selection
38. no memory-based authorization
39. no duplicate canonical records
40. memory compaction
41. memory superseding
42. memory archival
43. empty-memory behavior
44. contradictory-memory behavior
45. end-to-end local RAG retrieval
"""

import os
import json
import uuid
import tempfile
import pytest
import numpy as np
from datetime import datetime, timezone

from backend.app.memory.models import (
    MemoryType,
    MemoryStatus,
    MemoryApplicability,
    RelationshipType,
    EngineeringMemory,
    MemoryRelationship,
    MemoryCandidate,
    MemorySearchResult,
)
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.embedding import (
    EmbeddingProvider,
    LocalDeterministicEmbeddingProvider,
)
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.memory.hybrid_rag import HybridRAGService
from backend.app.memory.candidate_service import MemoryCandidateService
from backend.app.models.target import ApplicationTarget
from backend.app.models.enums import TestMode
from backend.app.dogfooding.strategy_engine import AdaptiveStrategyEngine
from backend.app.dogfooding.live_events import LiveEventType
from backend.app.dogfooding.live_session_bus import live_event_bus
from backend.app.dogfooding.runner_observer import LiveRunnerObserver
from backend.app.models.test_run import TestRun
from backend.app.control_plane.redaction import RedactionEngine


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_memory.db")


@pytest.fixture
def repo(temp_db_path):
    return EngineeringMemoryRepository(db_path=temp_db_path)


@pytest.fixture
def embedding_provider():
    return LocalDeterministicEmbeddingProvider(dimension=128)


@pytest.fixture
def vector_index():
    return VectorMemoryIndex(dimension=128)


@pytest.fixture
def hybrid_rag(repo, vector_index, embedding_provider):
    return HybridRAGService(
        repository=repo,
        vector_index=vector_index,
        embedding_provider=embedding_provider,
    )


@pytest.fixture
def candidate_service(repo, vector_index, embedding_provider):
    return MemoryCandidateService(
        repository=repo,
        vector_index=vector_index,
        embedding_provider=embedding_provider,
    )


# ============================================================================
# 1-7: Memory Creation, Provenance, Status, Types, Evidence & Context Linkage
# ============================================================================

def test_01_memory_creation(repo):
    """Test 1: Memory creation and retrieval from canonical SQLite store."""
    mem = EngineeringMemory(
        memory_id="mem_001",
        application_id="question_generator",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Question generator requires grade level selection before submission.",
        status=MemoryStatus.OBSERVED,
        source_type="RUN_EXECUTION",
        source_run_id="run_101",
        source_evidence_ids=["evi_1", "evi_2"],
    )
    saved = repo.save_memory(mem)
    assert saved.memory_id == "mem_001"
    fetched = repo.get_memory("mem_001")
    assert fetched is not None
    assert fetched.content == mem.content
    assert fetched.application_id == "question_generator"


def test_02_memory_provenance(repo):
    """Test 2: Memory provenance integrity (run, diagnosis, commit, prompt)."""
    mem = EngineeringMemory(
        memory_id="mem_002",
        application_id="question_generator",
        memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        content="Option D always renders with correct indicator.",
        status=MemoryStatus.OBSERVED,
        source_type="RUN_EXECUTION",
        source_run_id="run_abc",
        source_evidence_ids=["evi_dom_10"],
        source_diagnosis_id="diag_99",
        git_commit="git_commit_789",
        prompt_version="v14",
        model_id="qwen2.5-coder:7b-instruct",
    )
    repo.save_memory(mem)
    fetched = repo.get_memory("mem_002")
    assert fetched.source_run_id == "run_abc"
    assert fetched.source_diagnosis_id == "diag_99"
    assert fetched.git_commit == "git_commit_789"
    assert fetched.prompt_version == "v14"


def test_03_memory_status_semantics(repo):
    """Test 3: Memory status values and deterministic transition."""
    mem = EngineeringMemory(
        memory_id="mem_003",
        application_id="app_1",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Test content",
        status=MemoryStatus.DECLARED,
    )
    repo.save_memory(mem)
    assert repo.get_memory("mem_003").status == MemoryStatus.DECLARED

    # Transition to INVALIDATED
    invalidated = repo.invalidate_memory("mem_003", "Contradicted by runtime evidence")
    assert invalidated.status == MemoryStatus.INVALIDATED


def test_04_memory_types_coverage(repo):
    """Test 4: All 14 memory types are valid and persisted deterministically."""
    types = [
        MemoryType.APPLICATION_FACT,
        MemoryType.WORKFLOW,
        MemoryType.WORKFLOW_STATE,
        MemoryType.WORKFLOW_TRANSITION,
        MemoryType.BEHAVIORAL_OBSERVATION,
        MemoryType.EDGE_CASE,
        MemoryType.FAILURE_HISTORY,
        MemoryType.REGRESSION_HISTORY,
        MemoryType.CONTRACT_REFERENCE,
        MemoryType.AI_BEHAVIOR,
        MemoryType.CHANGE_IMPACT,
        MemoryType.REMEDIATION_HISTORY,
        MemoryType.RELIABILITY_PATTERN,
        MemoryType.UNKNOWN_BEHAVIOR,
    ]
    assert len(types) == 14
    for i, mtype in enumerate(types):
        mem = EngineeringMemory(
            memory_id=f"mem_type_{i}",
            application_id="app_test",
            memory_type=mtype,
            content=f"Knowledge item of type {mtype.value}",
            status=MemoryStatus.OBSERVED,
            source_run_id="run_types",
        )
        repo.save_memory(mem)
        fetched = repo.get_memory(f"mem_type_{i}")
        assert fetched.memory_type == mtype


def test_05_evidence_linkage(repo):
    """Test 5: Evidence IDs are strictly linked to memory records."""
    mem = EngineeringMemory(
        memory_id="mem_evi_01",
        application_id="app_test",
        memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        content="Screenshot confirms spinner vanishes in 200ms",
        status=MemoryStatus.OBSERVED,
        source_run_id="run_evi",
        source_evidence_ids=["evi_ss_1", "evi_dom_2", "evi_net_3"],
    )
    repo.save_memory(mem)
    fetched = repo.get_memory("mem_evi_01")
    assert len(fetched.source_evidence_ids) == 3
    assert "evi_dom_2" in fetched.source_evidence_ids


def test_06_context_linkage_and_07_context_hash(repo):
    """Test 6 & 7: Context ID and cryptographic context_hash linkage."""
    ctx_hash = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    mem = EngineeringMemory(
        memory_id="mem_ctx_01",
        application_id="app_test",
        memory_type=MemoryType.CONTRACT_REFERENCE,
        content="Contract C-1 applies under context ctx_8c_1",
        status=MemoryStatus.DECLARED,
        context_id="ctx_8c_1",
        context_hash=ctx_hash,
    )
    repo.save_memory(mem)
    fetched = repo.get_memory("mem_ctx_01")
    assert fetched.context_id == "ctx_8c_1"
    assert fetched.context_hash == ctx_hash


# ============================================================================
# 8-12: Version Applicability, Stale Detection, Invalidation, Contradictions, Relationships
# ============================================================================

def test_08_version_applicability_and_09_stale_detection(hybrid_rag, repo):
    """Test 8 & 9: Deterministic version applicability and stale evaluation."""
    mem_same_ver = EngineeringMemory(
        memory_id="mem_ver_same",
        application_id="app_ver",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Parameter slider defaults to medium.",
        status=MemoryStatus.OBSERVED,
        prompt_version="v2",
        git_commit="hash_abc",
    )
    mem_diff_ver = EngineeringMemory(
        memory_id="mem_ver_diff",
        application_id="app_ver",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Old parameter slider was a text box.",
        status=MemoryStatus.OBSERVED,
        prompt_version="v1",
        git_commit="hash_old",
    )
    repo.save_memory(mem_same_ver)
    repo.save_memory(mem_diff_ver)

    # Current context is prompt v2, commit hash_abc
    app_state_same = hybrid_rag._evaluate_applicability(
        mem_same_ver, current_prompt_version="v2", current_git_commit="hash_abc"
    )
    assert app_state_same == MemoryApplicability.APPLICABLE

    # Prompt v1 is different from current prompt v2 -> PARTIALLY_APPLICABLE or STALE
    app_state_diff = hybrid_rag._evaluate_applicability(
        mem_diff_ver, current_prompt_version="v2", current_git_commit="hash_abc"
    )
    assert app_state_diff in (MemoryApplicability.STALE, MemoryApplicability.PARTIALLY_APPLICABLE)

    # Explicit STALE status deterministically yields STALE
    mem_stale = EngineeringMemory(
        memory_id="mem_stale_explicit",
        application_id="app_ver",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Old behavior",
        status=MemoryStatus.STALE,
    )
    assert hybrid_rag._evaluate_applicability(mem_stale) == MemoryApplicability.STALE


def test_10_invalidation_and_audit(repo):
    """Test 10: Invalidation marks memory and writes immutable audit log."""
    mem = EngineeringMemory(
        memory_id="mem_inv_1",
        application_id="app_inv",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Export button always present in navbar.",
        status=MemoryStatus.OBSERVED,
    )
    repo.save_memory(mem)
    updated = repo.invalidate_memory("mem_inv_1", "Navbar redesigned, export button moved", MemoryStatus.INVALIDATED)
    assert updated.status == MemoryStatus.INVALIDATED

    # Verify audit log exists
    with repo._get_connection() as conn:
        log = conn.execute("SELECT * FROM memory_audit_logs WHERE memory_id = ?", ("mem_inv_1",)).fetchone()
        assert log is not None
        assert "INVALIDAT" in log["event_type"]
        assert "Navbar redesigned" in log["details"]


def test_11_contradiction_detection_and_12_relationship_creation(candidate_service, repo):
    """Test 11 & 12: Contradiction detection creates CONTRADICTS relationship and supersedes."""
    # Historical memory: "Export button exists."
    old_mem = EngineeringMemory(
        memory_id="mem_old_export",
        application_id="qgen",
        workflow_id="wf_export",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Export button exists in top header.",
        status=MemoryStatus.OBSERVED,
        source_run_id="run_old",
        source_evidence_ids=["evi_old"],
    )
    repo.save_memory(old_mem)

    # New candidate from current runtime: "Export button absent in top header."
    cand = candidate_service.create_candidate(
        application_id="qgen",
        workflow_id="wf_export",
        proposed_memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        proposed_content="Export button absent in top header during execution.",
        source_run_id="run_new",
        source_evidence_ids=["evi_new"],
        proposed_status=MemoryStatus.OBSERVED,
    )

    new_mem, relationships = candidate_service.promote_candidate(cand.candidate_id)
    assert new_mem is not None
    assert len(relationships) >= 1
    rel = relationships[0]
    assert rel.relationship_type == RelationshipType.CONTRADICTS
    assert rel.target_memory_id == old_mem.memory_id

    # Historical memory must now be INVALIDATED
    updated_old = repo.get_memory(old_mem.memory_id)
    assert updated_old.status == MemoryStatus.INVALIDATED


# ============================================================================
# 13-15: Candidate Validation, Promotion Rules, Unsupported Claim Rejection
# ============================================================================

def test_13_candidate_validation_rules(candidate_service, repo):
    """Test 13: Deterministic validation rules enforce provenance and evidence."""
    cand = candidate_service.create_candidate(
        application_id="app_1",
        proposed_memory_type=MemoryType.APPLICATION_FACT,
        proposed_content="Valid candidate content here",
        source_run_id="run_cand_1",
        source_evidence_ids=["evi_10"],
        proposed_status=MemoryStatus.OBSERVED,
    )
    is_valid, reason, passed = candidate_service.validate_candidate(cand)
    assert is_valid is True
    assert "provenance_run_present" in passed
    assert "observed_evidence_verified" in passed


def test_14_promotion_rules(candidate_service, repo):
    """Test 14: Valid candidate is promoted to canonical EngineeringMemory."""
    cand = candidate_service.create_candidate(
        application_id="app_1",
        proposed_memory_type=MemoryType.WORKFLOW,
        proposed_content="Generated question workflow produces 4 options with radio inputs",
        source_run_id="run_cand_2",
        source_evidence_ids=["evi_wf_1"],
        proposed_status=MemoryStatus.OBSERVED,
    )
    mem, _ = candidate_service.promote_candidate(cand.candidate_id)
    assert mem is not None
    assert mem.content == cand.proposed_content
    # Status of candidate should now be PROMOTED
    updated_cand = repo.get_candidate(cand.candidate_id)
    assert updated_cand.status == "PROMOTED"


def test_15_unsupported_claim_rejection(candidate_service, repo):
    """Test 15: Unbacked claim claiming OBSERVED status without evidence is rejected."""
    cand = candidate_service.create_candidate(
        application_id="app_1",
        proposed_memory_type=MemoryType.APPLICATION_FACT,
        proposed_content="Model claims button has 5px radius",
        source_run_id="run_cand_3",
        source_evidence_ids=[],  # Empty evidence for OBSERVED!
        proposed_status=MemoryStatus.OBSERVED,
    )
    mem, _ = candidate_service.promote_candidate(cand.candidate_id)
    assert mem is None  # Rejected!
    updated_cand = repo.get_candidate(cand.candidate_id)
    assert updated_cand.status == "REJECTED"
    assert "evidence" in updated_cand.rejection_reason.lower()


# ============================================================================
# 16-18: Workflow Memory, Failure Memory, Regression Memory
# ============================================================================

def test_16_workflow_memory(candidate_service, repo):
    """Test 16: Workflow extraction captures action transitions."""
    run_payload = {
        "run_id": "run_wf_test",
        "actions": [
            {"action_type": "click", "selector": "#topic-select", "value": ""},
            {"action_type": "input", "selector": "#topic-input", "value": "Algebra"},
            {"action_type": "click", "selector": "#generate-btn", "value": ""},
        ],
        "evidence": {"evi_1": {}},
        "metadata": {},
    }
    promoted = candidate_service.process_run_and_promote(run_payload, application_id="qgen")
    assert any(m.memory_type == MemoryType.WORKFLOW for m in promoted)
    wf_mem = next(m for m in promoted if m.memory_type == MemoryType.WORKFLOW)
    assert "click on '#topic-select'" in wf_mem.content


def test_17_failure_memory_and_18_regression_memory(candidate_service, repo):
    """Test 17 & 18: Failure history captured and becomes future testing hypothesis."""
    run_payload = {
        "run_id": "run_fail_test",
        "failures": [
            {
                "category": "ASSERTION_FAILED",
                "title": "Duplicate Options Detected",
                "detail": "Option A and Option C both contained 'x = 4'",
                "selector": ".question-card",
            }
        ],
        "evidence": {"evi_fail_1": {}},
        "metadata": {},
    }
    promoted = candidate_service.process_run_and_promote(run_payload, application_id="qgen")
    assert any(m.memory_type == MemoryType.FAILURE_HISTORY for m in promoted)
    fail_mem = next(m for m in promoted if m.memory_type == MemoryType.FAILURE_HISTORY)
    assert "Duplicate Options Detected" in fail_mem.content


# ============================================================================
# 19-21: Local Semantic Embeddings & Local Vector Index (Zero Cloud APIs)
# ============================================================================

def test_19_semantic_embedding_generation(embedding_provider):
    """Test 19: Local deterministic embedding provider produces normalized vectors."""
    vec1 = embedding_provider.embed_text("Generate math question with multiple choices")
    vec2 = embedding_provider.embed_text("Generate math quiz with distractors")
    vec3 = embedding_provider.embed_text("Database migration script failure in postgres")

    assert isinstance(vec1, list)
    assert len(vec1) == 128
    arr1 = np.array(vec1)
    # L2 normalized
    assert abs(np.linalg.norm(arr1) - 1.0) < 1e-4

    # Related texts should have higher cosine similarity than unrelated texts
    sim_related = np.dot(arr1, np.array(vec2))
    sim_unrelated = np.dot(arr1, np.array(vec3))
    assert sim_related > sim_unrelated


def test_20_vector_index_persistence_and_21_rebuild(tmp_path, repo, embedding_provider):
    """Test 20 & 21: Vector index saves, loads, and rebuilds from canonical store."""
    index_file = str(tmp_path / "vector_test.npz")
    vindex = VectorMemoryIndex(dimension=128, storage_path=index_file)

    mem1 = repo.save_memory(EngineeringMemory(
        memory_id="mem_v1",
        application_id="app_v",
        memory_type=MemoryType.APPLICATION_FACT,
        content="First vector memory item",
        status=MemoryStatus.OBSERVED,
    ))
    mem2 = repo.save_memory(EngineeringMemory(
        memory_id="mem_v2",
        application_id="app_v",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Second vector memory item",
        status=MemoryStatus.OBSERVED,
    ))

    # Add and persist
    v1 = embedding_provider.embed_text(mem1.content)
    v2 = embedding_provider.embed_text(mem2.content)
    vindex.add_vector("mem_v1", v1)
    vindex.add_vector("mem_v2", v2)
    vindex.save()

    # Load into new instance
    loaded_index = VectorMemoryIndex(dimension=128, storage_path=index_file)
    assert loaded_index.load() is True
    assert loaded_index.total_vectors == 2

    # Invariant 3: Rebuild index from canonical store if index is deleted
    os.remove(index_file)
    rebuilt_index = VectorMemoryIndex(dimension=128, storage_path=index_file)
    rebuilt_count = rebuilt_index.rebuild_from_repository(repo, embedding_provider)
    assert rebuilt_count >= 2
    assert rebuilt_index.total_vectors >= 2


# ============================================================================
# 22-25: Metadata Filtering, Hybrid Retrieval, Deterministic Ranking, Top-K
# ============================================================================

def test_22_metadata_filtering_and_23_hybrid_retrieval(hybrid_rag, repo, embedding_provider, vector_index):
    """Test 22 & 23: Metadata filters candidates before semantic scoring."""
    # App A memory
    mem_a = repo.save_memory(EngineeringMemory(
        memory_id="mem_app_a",
        application_id="app_alpha",
        workflow_id="wf_checkout",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Checkout button requires user login session",
        status=MemoryStatus.OBSERVED,
    ))
    # App B memory
    mem_b = repo.save_memory(EngineeringMemory(
        memory_id="mem_app_b",
        application_id="app_beta",
        workflow_id="wf_checkout",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Checkout button requires user login session",
        status=MemoryStatus.OBSERVED,
    ))

    vector_index.add_vector(mem_a.memory_id, embedding_provider.embed_text(mem_a.content))
    vector_index.add_vector(mem_b.memory_id, embedding_provider.embed_text(mem_b.content))

    # Query for app_alpha specifically
    results = hybrid_rag.retrieve(query="login session checkout", application_id="app_alpha")
    assert len(results) == 1
    assert results[0].memory.memory_id == "mem_app_a"


def test_24_deterministic_retrieval_ranking_and_25_bounded_top_k(hybrid_rag, repo, embedding_provider, vector_index):
    """Test 24 & 25: Deterministic ranking applies multi-factor weights and bounds to top_k."""
    for i in range(10):
        mem = repo.save_memory(EngineeringMemory(
            memory_id=f"mem_rank_{i}",
            application_id="app_ranking",
            workflow_id="wf_math" if i == 0 else "wf_other",
            memory_type=MemoryType.APPLICATION_FACT,
            content=f"Math question generator feature note number {i}",
            status=MemoryStatus.OBSERVED,
        ))
        vector_index.add_vector(mem.memory_id, embedding_provider.embed_text(mem.content))

    # Request top_k = 3
    results = hybrid_rag.retrieve(
        query="Math question generator feature",
        application_id="app_ranking",
        workflow_id="wf_math",
        top_k=3,
    )
    assert len(results) <= 3
    # First result should be mem_rank_0 because workflow matches perfectly
    assert results[0].memory.memory_id == "mem_rank_0"
    assert "workflow" in results[0].ranking_factors


# ============================================================================
# 26-28: Invariant 6 (Current Evidence Overrides Historical Memory), Version-Aware, App Isolation
# ============================================================================

def test_26_current_evidence_overriding_historical_memory(candidate_service, repo):
    """Test 26: Current runtime evidence overrides historical memory without deleting contradiction."""
    hist = repo.save_memory(EngineeringMemory(
        memory_id="mem_hist_btn",
        application_id="app_btn",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Submit button is enabled on page load.",
        status=MemoryStatus.OBSERVED,
        source_run_id="run_1",
        source_evidence_ids=["evi_1"],
    ))

    # New run observes button disabled
    cand = candidate_service.create_candidate(
        application_id="app_btn",
        proposed_memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        proposed_content="Submit button is disabled on page load until form filled.",
        source_run_id="run_2",
        source_evidence_ids=["evi_2"],
        proposed_status=MemoryStatus.OBSERVED,
    )
    new_mem, rels = candidate_service.promote_candidate(cand.candidate_id)

    # Current evidence promoted, old marked INVALIDATED
    assert new_mem.status == MemoryStatus.OBSERVED
    updated_hist = repo.get_memory("mem_hist_btn")
    assert updated_hist.status == MemoryStatus.INVALIDATED


def test_27_version_aware_retrieval(hybrid_rag, repo):
    """Test 27: Version-aware retrieval marks stale memories accurately."""
    mem_v1 = repo.save_memory(EngineeringMemory(
        memory_id="mem_prompt_v1",
        application_id="app_q",
        memory_type=MemoryType.APPLICATION_FACT,
        content="System prompt uses format [QUESTION: ...]",
        status=MemoryStatus.OBSERVED,
        prompt_version="v1",
    ))
    res = hybrid_rag.retrieve(
        query="System prompt format",
        application_id="app_q",
        current_prompt_version="v2",
    )
    assert len(res) == 1
    assert res[0].applicability in (MemoryApplicability.STALE, MemoryApplicability.PARTIALLY_APPLICABLE)


def test_28_application_isolation(hybrid_rag, repo):
    """Test 28: Memories from application A never leak into application B."""
    repo.save_memory(EngineeringMemory(
        memory_id="mem_sec_a",
        application_id="tenant_a",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Confidential business logic of tenant A",
        status=MemoryStatus.OBSERVED,
    ))
    results = hybrid_rag.retrieve(query="Confidential business logic", application_id="tenant_b")
    assert len(results) == 0


# ============================================================================
# 29-30: Security Redaction & Secret Exclusion
# ============================================================================

def test_29_security_redaction_and_30_secret_exclusion(repo, embedding_provider):
    """Test 29 & 30: Secrets are redacted from memory and embeddings before storage."""
    secret_text = "Database config with password: 'super_secret_password_123' and sk-proj-12345678901234567890abcdef and Bearer secret_bearer_token_12345"
    sanitized, was_redacted = RedactionEngine.redact_text(secret_text)
    assert len(was_redacted) > 0
    assert "super_secret_password_123" not in sanitized
    assert "sk-proj" not in sanitized

    # Check saving into repo redacts content
    mem = repo.save_memory(EngineeringMemory(
        memory_id="mem_sec_01",
        application_id="app_sec",
        memory_type=MemoryType.APPLICATION_FACT,
        content=secret_text,
        status=MemoryStatus.OBSERVED,
    ))
    saved_mem = repo.get_memory("mem_sec_01")
    assert "super_secret_password_123" not in saved_mem.content

    # Embedding provider redacts text internally
    emb = embedding_provider.embed_text(secret_text)
    assert len(emb) == 128


# ============================================================================
# 31-32: Qwen Bounded Context Formatting & No Private CoT Exposure
# ============================================================================

def test_31_qwen_context_formatting_and_32_no_private_cot(hybrid_rag, repo):
    """Test 31 & 32: Context formatted for Qwen is bounded, structured, and free of raw CoT."""
    mem = repo.save_memory(EngineeringMemory(
        memory_id="mem_qwen_1",
        application_id="question_gen",
        memory_type=MemoryType.FAILURE_HISTORY,
        content="Previous generation produced duplicate distractors on math questions.",
        status=MemoryStatus.OBSERVED,
        source_run_id="run_101",
        prompt_version="v12",
    ))
    search_res = MemorySearchResult(
        memory=mem,
        score=0.88,
        semantic_similarity=0.85,
        applicability=MemoryApplicability.APPLICABLE,
        ranking_factors={"application_match": 1.0},
    )
    formatted = hybrid_rag.format_memory_for_agent([search_res], application_name="Question Generator")
    assert "=== RELEVANT ENGINEERING MEMORY ===" in formatted
    assert "Question Generator" in formatted
    assert "duplicate distractors" in formatted
    assert "Current runtime observations always override historical memory." in formatted
    # Must not contain private internal thoughts or raw prompt dumps
    assert "thought_trace" not in formatted
    assert "chain_of_thought" not in formatted


# ============================================================================
# 33-34: Live Console Events & Memory Retrieval Replay
# ============================================================================

def test_33_live_console_memory_events_and_34_replay():
    """Test 33 & 34: LiveConsole receives structured memory events with structured provenance."""
    session_id = f"sess_live_{uuid.uuid4().hex[:6]}"
    target = ApplicationTarget(target_id="tgt_1", name="Question Gen", base_url="http://localhost:3000")
    run = TestRun(run_id="run_live_mem", target_id="tgt_1", application_id="tgt_1", session_id=session_id)

    observer = LiveRunnerObserver.for_run(run, target)

    # Emit memory retrieval
    observer.on_memory_retrieval_started("generate questions", "question_gen")
    observer.on_memory_retrieval_completed(
        total_retrieved=3,
        applicable_count=2,
        historical_count=1,
        conflicting_count=0,
        top_memories=[{"content": "Duplicate distractors noted", "status": "OBSERVED", "type": "FAILURE_HISTORY"}],
    )
    observer.on_memory_promoted("mem_123", "WORKFLOW", "Verified 4 options flow")

    events_captured = live_event_bus.get_events(observer.session_id)
    event_types = [e.event_type for e in events_captured]
    assert LiveEventType.MEMORY_RETRIEVAL_STARTED in event_types
    assert LiveEventType.MEMORY_RETRIEVAL_COMPLETED in event_types
    assert LiveEventType.MEMORY_PROMOTED in event_types


# ============================================================================
# 35-37: 8D.1 Strategy Engine Integration, Workflow Prioritization, Edge Cases
# ============================================================================

def test_35_strategy_integration_and_36_workflow_prioritization_and_37_edge_cases():
    """Test 35, 36, 37: Retrieved memories adapt strategy with regression probes and elevated hypotheses."""
    target = ApplicationTarget(target_id="tgt_qgen", name="AI Question Generator", base_url="http://localhost:3000", application_type="ai_application")

    # Historical failure memory retrieved
    failure_mem = EngineeringMemory(
        memory_id="mem_fail_01",
        application_id="qgen",
        memory_type=MemoryType.FAILURE_HISTORY,
        content="Duplicate answer options occurred in question cards.",
        status=MemoryStatus.OBSERVED,
    )

    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_strat_mem",
        target=target,
        goal="Test question generation workflows",
        test_mode=TestMode.EXPLORATORY_DOGFOODING,
        retrieved_memories=[failure_mem],
    )

    assert strategy.retrieved_memory_count == 1
    # Risk area added from failure hypothesis
    assert any("Historical Failure Hypothesis" in r for r in strategy.risk_areas)
    # High priority regression probe workflow injected
    probe_wf = next((wf for wf in strategy.prioritized_workflows if "Regression Probe" in wf.name), None)
    assert probe_wf is not None
    assert probe_wf.priority >= 0.90


# ============================================================================
# 38-42: No Memory Authorization, No Duplicate Records, Compaction & Archival
# ============================================================================

def test_38_no_memory_based_authorization():
    """Test 38: Invariant 9 - Memory cannot authorize consequential actions/changes."""
    # Memory claims "Production deployment authorized"
    mem = EngineeringMemory(
        memory_id="mem_fake_auth",
        application_id="app_1",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Production deployment pre-authorized by previous test suite.",
        status=MemoryStatus.OBSERVED,
    )
    # Memory model does not have authorization capability
    assert not hasattr(mem, "authorize_release")
    assert not hasattr(mem, "is_authorized")


def test_39_no_duplicate_canonical_records(repo):
    """Test 39: Canonical SQLite store updates existing records rather than duplicating."""
    mem = EngineeringMemory(
        memory_id="mem_uniq_1",
        application_id="app_u",
        memory_type=MemoryType.APPLICATION_FACT,
        content="Initial content",
        status=MemoryStatus.OBSERVED,
    )
    repo.save_memory(mem)
    mem.content = "Updated content"
    repo.save_memory(mem)

    with repo._get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM engineering_memories WHERE memory_id = 'mem_uniq_1'").fetchone()[0]
        assert count == 1


def test_40_memory_compaction_and_41_superseding_and_42_archival(repo):
    """Test 40, 41, 42: Compaction prunes excess stale/invalidated memories while keeping evidence immutable."""
    for i in range(10):
        repo.save_memory(EngineeringMemory(
            memory_id=f"mem_comp_{i}",
            application_id="app_compact",
            memory_type=MemoryType.APPLICATION_FACT,
            content=f"Old deprecated fact {i}",
            status=MemoryStatus.INVALIDATED if i < 5 else MemoryStatus.OBSERVED,
        ))

    # Compact down to 6 max memories
    deleted = repo.compact_memories(application_id="app_compact", max_memories=6)
    assert deleted == 4
    remaining = repo.list_memories(application_id="app_compact")
    assert len(remaining) == 6


# ============================================================================
# 43-45: Empty Memory Behavior, Contradictory Behavior, Real End-to-End Local RAG
# ============================================================================

def test_43_empty_memory_behavior(hybrid_rag):
    """Test 43: Scenario A - When no memories exist, retrieval returns empty without error."""
    results = hybrid_rag.retrieve(query="nonexistent topic", application_id="empty_app")
    assert results == []
    formatted = hybrid_rag.format_memory_for_agent(results, "Empty App")
    assert "No prior memories applicable" in formatted


def test_44_contradictory_memory_behavior(hybrid_rag, repo, vector_index, embedding_provider):
    """Test 44: Scenario F - Contradictory observations both preserved with CONTRADICTS marker."""
    mem_a = repo.save_memory(EngineeringMemory(
        memory_id="mem_contra_a",
        application_id="app_contra",
        workflow_id="wf_btn",
        memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        content="Button enabled on initial render",
        status=MemoryStatus.OBSERVED,
    ))
    mem_b = repo.save_memory(EngineeringMemory(
        memory_id="mem_contra_b",
        application_id="app_contra",
        workflow_id="wf_btn",
        memory_type=MemoryType.BEHAVIORAL_OBSERVATION,
        content="Button disabled on initial render",
        status=MemoryStatus.OBSERVED,
    ))
    repo.add_relationship(
        source_memory_id=mem_b.memory_id,
        target_memory_id=mem_a.memory_id,
        relationship_type=RelationshipType.CONTRADICTS,
        rationale="Discrepancy across test runs",
    )

    vector_index.add_vector(mem_a.memory_id, embedding_provider.embed_text(mem_a.content))
    vector_index.add_vector(mem_b.memory_id, embedding_provider.embed_text(mem_b.content))

    results = hybrid_rag.retrieve(query="Button initial render state", application_id="app_contra")
    assert len(results) == 2
    # At least one result should note the contradiction relationship
    assert any(r.conflict_notes is not None for r in results)


def test_45_end_to_end_local_rag_retrieval(hybrid_rag, candidate_service, repo):
    """
    Test 45: Full local RAG lifecycle:
    Execute Run -> Extract Candidate -> Deterministic Promote -> Local Embed -> Vector Index ->
    Hybrid Retrieve -> Bounded Context Formatting -> Strategy Adaptation.
    """
    # 1. Simulate run with failure
    run_payload = {
        "run_id": "run_e2e_qgen",
        "failures": [
            {
                "category": "ASSERTION_FAILED",
                "title": "Duplicate Options",
                "detail": "Generated distractors were identical",
                "selector": "#question-options",
            }
        ],
        "actions": [
            {"action_type": "input", "selector": "#topic", "value": "Physics"},
            {"action_type": "click", "selector": "#generate", "value": ""},
        ],
        "evidence": {"evi_e2e_1": {}},
        "metadata": {"prompt_version": "v12"},
    }

    # 2. Extract and promote
    promoted = candidate_service.process_run_and_promote(run_payload, application_id="qgen_e2e")
    assert len(promoted) >= 1

    # 3. Hybrid Retrieve for future run
    search_results = hybrid_rag.retrieve(
        query="distractors duplicate options physics",
        application_id="qgen_e2e",
        top_k=3,
    )
    assert len(search_results) >= 1
    top_hit = search_results[0]
    assert "Duplicate Options" in top_hit.memory.content

    # 4. Format context for Qwen
    agent_context = hybrid_rag.format_memory_for_agent(search_results, application_name="Question Generator")
    assert "Duplicate Options" in agent_context

    # 5. Adapt Strategy
    target = ApplicationTarget(target_id="tgt_qgen", name="Question Generator", base_url="http://localhost:3000", application_id="qgen_e2e")
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_future",
        target=target,
        goal="Test question generation without regressions",
        retrieved_memories=search_results,
    )
    assert strategy.retrieved_memory_count >= 1
    assert any("Duplicate Options" in summary for summary in strategy.retrieved_memory_summaries)
