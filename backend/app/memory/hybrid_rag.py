"""
Slice 8E — Hybrid RAG Retrieval Engine

Executes multi-stage hybrid retrieval:
1. Deterministic metadata filtering
2. Local semantic vector similarity over candidate population
3. Context version applicability evaluation
4. Conflict and contradiction resolution
5. Multi-factor deterministic ranking
6. Bounded context preparation for Qwen 2.5-Coder 7B
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple, Union
import logging

from backend.app.memory.models import (
    EngineeringMemory,
    MemorySearchResult,
    MemoryApplicability,
    MemoryStatus,
    MemoryType,
)
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.embedding import EmbeddingProvider, LocalDeterministicEmbeddingProvider
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.control_plane.redaction import RedactionEngine

logger = logging.getLogger("ai_qa_platform.hybrid_rag")


class HybridRAGService:
    """
    Retrieves and ranks relevant engineering memories for testing sessions.
    Guarantees deterministic ranking and bounded context sizes.
    """

    def __init__(
        self,
        repository: EngineeringMemoryRepository,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_index: Optional[VectorMemoryIndex] = None,
    ):
        self.repo = repository
        self.embedder = embedding_provider or LocalDeterministicEmbeddingProvider()
        self.vector_index = vector_index or VectorMemoryIndex(dimension=self.embedder.dimension)

    def evaluate_applicability(
        self,
        memory: EngineeringMemory,
        current_application_id: Optional[str] = None,
        current_git_commit: Optional[str] = None,
        current_prompt_version: Optional[Union[str, int]] = None,
        current_model_id: Optional[str] = None,
    ) -> MemoryApplicability:
        return memory.evaluate_applicability(
            current_application_id=current_application_id or memory.application_id,
            current_git_commit=current_git_commit,
            current_prompt_version=current_prompt_version,
            current_model_id=current_model_id,
        )

    _evaluate_applicability = evaluate_applicability

    def retrieve(
        self,
        query: str,
        application_id: str,
        target_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        current_git_commit: Optional[str] = None,
        current_prompt_version: Optional[Union[str, int]] = None,
        current_model_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        include_historical: bool = True,
        top_k: int = 5,
        semantic_weight: float = 0.5,
    ) -> List[MemorySearchResult]:
        """
        Executes hybrid retrieval:
        1. Filters candidates by application_id and metadata.
        2. Applies semantic vector scoring over the filtered candidates.
        3. Evaluates version applicability and contradiction state.
        4. Calculates composite score using deterministic weights.
        5. Returns bounded Top-K results.
        """
        # Redact query before searching
        sanitized_query, _ = RedactionEngine.redact_text(query or "")

        # Step 1: Deterministic metadata filtering
        all_app_memories = self.repo.list_memories(application_id=application_id, limit=2000)
        if not all_app_memories:
            return []

        # Filter candidate subset
        candidates: List[EngineeringMemory] = []
        for mem in all_app_memories:
            if not include_historical and mem.status in (MemoryStatus.HISTORICAL, MemoryStatus.STALE, MemoryStatus.INVALIDATED):
                continue
            if memory_types and mem.memory_type not in memory_types:
                continue
            candidates.append(mem)

        if not candidates:
            return []

        candidate_ids = [m.memory_id for m in candidates]

        # Step 2: Semantic vector similarity over candidate population
        query_vector = self.embedder.embed_text(sanitized_query)
        semantic_scores: Dict[str, float] = {}

        if len(self.vector_index.memory_ids) > 0:
            hits = self.vector_index.search(
                query_vector=query_vector,
                k=len(candidate_ids),
                candidate_memory_ids=candidate_ids,
            )
            for mid, sim in hits:
                # Clamp similarity between 0.0 and 1.0
                semantic_scores[mid] = max(0.0, min(1.0, (sim + 1.0) / 2.0))
        else:
            # Vector index empty; compute fallback direct dot product
            candidate_texts = [m.content for m in candidates]
            candidate_vecs = self.embedder.embed_batch(candidate_texts)
            for m, vec in zip(candidates, candidate_vecs):
                sim = sum(a * b for a, b in zip(query_vector, vec))
                semantic_scores[m.memory_id] = max(0.0, min(1.0, (sim + 1.0) / 2.0))

        # Step 3: Multi-factor deterministic ranking
        ranked_results: List[MemorySearchResult] = []

        for mem in candidates:
            sem_sim = semantic_scores.get(mem.memory_id, 0.5)

            # Applicability factor
            applicability = mem.evaluate_applicability(
                current_application_id=application_id,
                current_git_commit=current_git_commit,
                current_prompt_version=current_prompt_version,
                current_model_id=current_model_id,
            )

            # Deterministic Factor Scoring:
            # 1. Application exact match: 1.0 (invariant)
            app_match = 1.0

            # 2. Workflow match: 1.0 if identical or unassigned, 0.4 if different
            wf_match = 1.0 if (not workflow_id or not mem.workflow_id or mem.workflow_id == workflow_id) else 0.4

            # 3. Status weight:
            status_weights = {
                MemoryStatus.OBSERVED: 1.0,
                MemoryStatus.DECLARED: 0.8,
                MemoryStatus.INFERRED: 0.7,
                MemoryStatus.HISTORICAL: 0.5,
                MemoryStatus.STALE: 0.3,
                MemoryStatus.UNKNOWN: 0.2,
                MemoryStatus.INVALIDATED: 0.0,
            }
            status_factor = status_weights.get(mem.status, 0.5)

            # 4. Applicability weight:
            applicability_weights = {
                MemoryApplicability.APPLICABLE: 1.0,
                MemoryApplicability.PARTIALLY_APPLICABLE: 0.7,
                MemoryApplicability.UNKNOWN: 0.4,
                MemoryApplicability.STALE: 0.2,
                MemoryApplicability.INVALIDATED: 0.0,
            }
            app_factor = applicability_weights.get(applicability, 0.5)

            # Composite Score:
            # W_sem: 0.35, W_app: 0.20, W_wf: 0.20, W_status: 0.15, W_applicability: 0.10
            composite_score = (
                (0.35 * sem_sim) +
                (0.20 * app_match) +
                (0.20 * wf_match) +
                (0.15 * status_factor) +
                (0.10 * app_factor)
            )

            # Look up conflicts / contradictions in relationships
            rels = self.repo.get_relationships(mem.memory_id)
            conflict_notes = None
            contradictions = [r for r in rels if r.relationship_type.value == "CONTRADICTS"]
            if contradictions:
                conflict_notes = f"Contradicted by {len(contradictions)} relationship(s): {contradictions[0].rationale}"

            ranked_results.append(
                MemorySearchResult(
                    memory=mem,
                    score=round(composite_score, 4),
                    semantic_similarity=round(sem_sim, 4),
                    applicability=applicability,
                    ranking_factors={
                        "semantic": round(sem_sim, 4),
                        "workflow": wf_match,
                        "status": status_factor,
                        "applicability": app_factor,
                    },
                    conflict_notes=conflict_notes,
                )
            )

        # Sort descending by composite score
        ranked_results.sort(key=lambda r: r.score, reverse=True)
        return ranked_results[:top_k]

    def format_memory_for_agent(
        self,
        retrieval_results: List[MemorySearchResult],
        application_name: str,
        current_workflow_name: Optional[str] = None,
    ) -> str:
        """
        Formats bounded, structured memory context for Qwen 2.5-Coder 7B.
        Invariant: Never exposes hidden LLM reasoning or raw memory dumps.
        """
        if not retrieval_results:
            return "=== ENGINEERING MEMORY ===\nNo prior memories applicable.\n========================="

        applicable_count = sum(1 for r in retrieval_results if r.applicability == MemoryApplicability.APPLICABLE)
        historical_count = sum(1 for r in retrieval_results if r.applicability in (MemoryApplicability.PARTIALLY_APPLICABLE, MemoryApplicability.STALE))
        conflict_count = sum(1 for r in retrieval_results if r.conflict_notes is not None)

        lines = [
            "=== RELEVANT ENGINEERING MEMORY ===",
            f"Application: {application_name}",
            f"Context: {applicable_count} applicable, {historical_count} historical, {conflict_count} conflicting",
            "Validated Knowledge from Previous Executions:",
        ]

        for i, res in enumerate(retrieval_results, 1):
            mem = res.memory
            status_tag = mem.status.value
            source_tag = f"Run: {mem.source_run_id}" if mem.source_run_id else "Evidence-derived"
            prompt_tag = f"Prompt v{mem.prompt_version}" if mem.prompt_version else ""
            tags = " | ".join(filter(None, [source_tag, prompt_tag]))

            lines.append(f"{i}. [{status_tag}] {mem.content}")
            lines.append(f"   Provenance: {tags} (Score: {res.score})")
            if res.conflict_notes:
                lines.append(f"   ⚠️ CONFLICT: {res.conflict_notes}")

        lines.append("Note: Current runtime observations always override historical memory.")
        lines.append("===================================")
        return "\n".join(lines)
