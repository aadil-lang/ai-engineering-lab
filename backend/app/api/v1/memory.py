"""
Slice 8E — Engineering Memory & Local Hybrid RAG API Router.
Provides structured REST endpoints for managing, searching, auditing,
and invalidating engineering memories.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.app.memory.models import (
    EngineeringMemory,
    MemorySearchResult,
    MemoryRelationship,
    MemoryStatus,
    MemoryType,
)
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.memory.embedding import LocalDeterministicEmbeddingProvider
from backend.app.memory.hybrid_rag import HybridRAGService

router = APIRouter()

# Shared singletons / default instances for API routes
_repo = EngineeringMemoryRepository()
_embedding_provider = LocalDeterministicEmbeddingProvider()
_vector_index = VectorMemoryIndex()
_hybrid_rag = HybridRAGService(
    repository=_repo,
    vector_index=_vector_index,
    embedding_provider=_embedding_provider,
)


def get_memory_repo() -> EngineeringMemoryRepository:
    return _repo


def get_hybrid_rag() -> HybridRAGService:
    return _hybrid_rag


class MemorySearchRequest(BaseModel):
    query: str
    application_id: Optional[str] = None
    target_id: Optional[str] = None
    component_id: Optional[str] = None
    workflow_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)
    current_prompt_version: Optional[str] = None
    current_git_commit: Optional[str] = None
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryInvalidateRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Deterministic justification for invalidating this memory")
    new_status: MemoryStatus = Field(default=MemoryStatus.INVALIDATED)


@router.get("", response_model=List[EngineeringMemory])
def list_memories(
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    status: Optional[MemoryStatus] = Query(None, description="Filter by memory status"),
    memory_type: Optional[MemoryType] = Query(None, description="Filter by memory type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """Lists engineering memories with deterministic metadata filtering."""
    return repo.list_memories(
        application_id=application_id,
        workflow_id=workflow_id,
        status=status,
        memory_type=memory_type,
        limit=limit,
        offset=offset,
    )


@router.get("/{memory_id}", response_model=EngineeringMemory)
def get_memory(
    memory_id: str,
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """Fetches a single engineering memory by its canonical ID."""
    memory = repo.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Engineering memory {memory_id} not found")
    return memory


@router.post("/search", response_model=List[MemorySearchResult])
def search_memories(
    request: MemorySearchRequest,
    rag: HybridRAGService = Depends(get_hybrid_rag),
):
    """
    Performs hybrid metadata + local semantic vector retrieval for relevant memories.
    Results are ranked deterministically with version applicability and conflict markers.
    """
    return rag.retrieve(
        query=request.query,
        application_id=request.application_id,
        target_id=request.target_id,
        component_id=request.component_id,
        workflow_id=request.workflow_id,
        top_k=request.top_k,
        current_prompt_version=request.current_prompt_version,
        current_git_commit=request.current_git_commit,
        semantic_weight=request.semantic_weight,
    )


@router.get("/{memory_id}/history")
def get_memory_history(
    memory_id: str,
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """Fetches the immutable audit trail of mutations for this memory."""
    memory = repo.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Engineering memory {memory_id} not found")

    with repo._get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_audit_logs WHERE memory_id = ? ORDER BY timestamp DESC",
            (memory_id,),
        ).fetchall()
        return [
            {
                "log_id": r["log_id"],
                "memory_id": r["memory_id"],
                "event_type": r["event_type"],
                "details": r["details"],
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]


@router.get("/{memory_id}/evidence")
def get_memory_evidence(
    memory_id: str,
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """Returns provenance and linked execution evidence IDs for this memory."""
    memory = repo.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Engineering memory {memory_id} not found")

    return {
        "memory_id": memory.memory_id,
        "source_type": memory.source_type,
        "source_run_id": memory.source_run_id,
        "source_evidence_ids": memory.source_evidence_ids,
        "source_diagnosis_id": memory.source_diagnosis_id,
        "context_id": memory.context_id,
        "context_hash": memory.context_hash,
        "git_commit": memory.git_commit,
        "prompt_version": memory.prompt_version,
    }


@router.get("/{memory_id}/relationships", response_model=List[MemoryRelationship])
def get_memory_relationships(
    memory_id: str,
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """Returns all explicit relationships (supports, contradicts, supersedes, etc.) for this memory."""
    memory = repo.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail=f"Engineering memory {memory_id} not found")
    return repo.get_relationships_for_memory(memory_id)


@router.post("/{memory_id}/invalidate", response_model=EngineeringMemory)
def invalidate_memory(
    memory_id: str,
    request: MemoryInvalidateRequest,
    repo: EngineeringMemoryRepository = Depends(get_memory_repo),
):
    """
    Deterministically marks a memory as INVALIDATED or STALE with reason and audit log.
    In accordance with Slice 8E invariants, historical memory is not deleted, preserving contradictions.
    """
    memory = repo.invalidate_memory(
        memory_id=memory_id,
        reason=request.reason,
        new_status=request.new_status,
    )
    if not memory:
        raise HTTPException(status_code=404, detail=f"Engineering memory {memory_id} not found")
    return memory
