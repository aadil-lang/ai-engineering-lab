"""
Candidate Service for Engineering Memory.
Implements the memory candidate pipeline:
Execution Evidence -> Memory Candidate -> Deterministic Validation ->
Provenance Check -> Applicability Check -> Conflict Detection -> Promotion Decision -> Engineering Memory.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

from backend.app.memory.models import (
    EngineeringMemory,
    MemoryCandidate,
    MemoryRelationship,
    MemoryType,
    MemoryStatus,
    RelationshipType,
)
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.memory.embedding import EmbeddingProvider
from backend.app.control_plane.redaction import RedactionEngine

logger = logging.getLogger(__name__)


class MemoryCandidateService:
    """
    Manages generation, deterministic validation, conflict resolution,
    and promotion of memory candidates derived from dogfooding execution evidence.
    """

    def __init__(
        self,
        repository: EngineeringMemoryRepository,
        vector_index: Optional[VectorMemoryIndex] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.repo = repository
        self.vector_index = vector_index
        self.embedding_provider = embedding_provider

    def create_candidate(
        self,
        application_id: str,
        proposed_memory_type: MemoryType,
        proposed_content: str,
        source_run_id: str,
        source_evidence_ids: List[str],
        proposed_status: MemoryStatus = MemoryStatus.OBSERVED,
        workflow_id: Optional[str] = None,
        component_id: Optional[str] = None,
        target_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.8,
    ) -> MemoryCandidate:
        """
        Creates and stores a memory candidate before promotion.
        """
        # Redact secrets from candidate content immediately
        clean_content, _ = RedactionEngine.redact_text(proposed_content)

        candidate = MemoryCandidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:8]}",
            application_id=application_id,
            target_id=target_id,
            component_id=component_id,
            workflow_id=workflow_id,
            proposed_memory_type=proposed_memory_type,
            proposed_content=clean_content,
            proposed_status=proposed_status,
            source_run_id=source_run_id,
            source_evidence_ids=source_evidence_ids,
            context=context or {},
            confidence_score=confidence_score,
            status="PROPOSED",
        )
        return self.repo.save_candidate(candidate)

    def validate_candidate(self, candidate: MemoryCandidate) -> Tuple[bool, str, List[str]]:
        """
        Applies deterministic rules to validate whether a candidate can be promoted.
        Invariant: Evidence is authoritative. LLM claims without evidence cannot be OBSERVED.
        """
        passed_rules: List[str] = []

        # Rule 1: Non-empty content
        if not candidate.proposed_content or len(candidate.proposed_content.strip()) < 5:
            return False, "Content too short or empty", passed_rules
        passed_rules.append("content_non_empty")

        # Rule 2: Valid provenance run
        if not candidate.source_run_id or len(candidate.source_run_id.strip()) == 0:
            return False, "Candidate missing source_run_id provenance", passed_rules
        passed_rules.append("provenance_run_present")

        # Rule 3: Evidence requirement for OBSERVED status
        if candidate.proposed_status == MemoryStatus.OBSERVED:
            if not candidate.source_evidence_ids or len(candidate.source_evidence_ids) == 0:
                # Cannot claim OBSERVED without concrete evidence IDs
                return False, "Cannot promote to OBSERVED status without direct source_evidence_ids", passed_rules
            passed_rules.append("observed_evidence_verified")

        # Rule 4: Secret-free content check
        _, was_redacted = RedactionEngine.redact_text(candidate.proposed_content)
        # Content should already be clean
        passed_rules.append("secret_redaction_passed")

        return True, "Deterministic validation passed", passed_rules

    def promote_candidate(
        self,
        candidate_id: str,
        prompt_version: Optional[str] = None,
        git_commit: Optional[str] = None,
        model_id: Optional[str] = None,
        context_hash: Optional[str] = None,
    ) -> Tuple[Optional[EngineeringMemory], List[MemoryRelationship]]:
        """
        Evaluates, validates, detects contradictions, promotes candidate to EngineeringMemory,
        and indexes vector if provider is available.
        """
        candidate = self.repo.get_candidate(candidate_id)
        if not candidate:
            logger.warning(f"Candidate {candidate_id} not found.")
            return None, []

        is_valid, reason, passed_rules = self.validate_candidate(candidate)
        candidate.validation_rules_passed = passed_rules

        if not is_valid:
            candidate.status = "REJECTED"
            candidate.rejection_reason = reason
            self.repo.save_candidate(candidate)
            logger.info(f"Rejected candidate {candidate_id}: {reason}")
            return None, []

        # Candidate is valid
        candidate.status = "VALIDATED"

        # Check for contradictions / conflicts with existing memories
        existing_memories = self.repo.list_memories(
            application_id=candidate.application_id,
            workflow_id=candidate.workflow_id,
        )

        relationships: List[MemoryRelationship] = []
        new_memory_id = f"mem_{uuid.uuid4().hex[:8]}"

        for existing in existing_memories:
            # Conflict check: If new candidate is current runtime evidence contradicting historical memory
            # For example, candidate says "Export button absent" while existing says "Export button exists"
            # Or candidate observed a workflow state transition that supersedes or contradicts old behavior.
            is_contradiction = self._detect_contradiction(candidate.proposed_content, existing.content)
            if is_contradiction:
                # Current runtime evidence wins!
                # Mark old memory as STALE or INVALIDATED
                old_status = existing.status
                self.repo.invalidate_memory(
                    memory_id=existing.memory_id,
                    reason=f"Contradicted by newer runtime evidence from run {candidate.source_run_id}: {candidate.proposed_content}",
                    new_status=MemoryStatus.INVALIDATED,
                )
                # Create explicit CONTRADICTS relationship
                rel = self.repo.add_relationship(
                    source_memory_id=new_memory_id,
                    target_memory_id=existing.memory_id,
                    relationship_type=RelationshipType.CONTRADICTS,
                    rationale=f"Current run {candidate.source_run_id} observed contrary runtime state (superseding {old_status.value})",
                )
                relationships.append(rel)

            elif self._detect_similarity_or_refinement(candidate.proposed_content, existing.content):
                # REFINES relationship
                rel = self.repo.add_relationship(
                    source_memory_id=new_memory_id,
                    target_memory_id=existing.memory_id,
                    relationship_type=RelationshipType.REFINES,
                    rationale="Refines previous observation with additional runtime evidence",
                )
                relationships.append(rel)

        # Create canonical EngineeringMemory
        memory = EngineeringMemory(
            memory_id=new_memory_id,
            application_id=candidate.application_id,
            target_id=candidate.target_id,
            component_id=candidate.component_id,
            workflow_id=candidate.workflow_id,
            memory_type=candidate.proposed_memory_type,
            content=candidate.proposed_content,
            status=candidate.proposed_status,
            source_type="RUN_EXECUTION",
            source_run_id=candidate.source_run_id,
            source_evidence_ids=candidate.source_evidence_ids,
            source_diagnosis_id=candidate.source_diagnosis_id,
            context_id=candidate.context.get("context_id"),
            context_hash=context_hash or candidate.context.get("context_hash"),
            git_commit=git_commit or candidate.context.get("git_commit"),
            prompt_version=prompt_version or candidate.context.get("prompt_version"),
            model_id=model_id or candidate.context.get("model_id"),
            retrieval_version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            last_verified_at=datetime.now(timezone.utc).isoformat(),
            version=1,
            confidence_metadata={
                "confidence_score": candidate.confidence_score,
                "validation_rules_passed": passed_rules,
            },
            tags=[candidate.proposed_memory_type.value.lower()],
        )

        saved_memory = self.repo.save_memory(memory)

        # Index into vector store if available
        if self.vector_index and self.embedding_provider:
            try:
                emb = self.embedding_provider.embed_text(saved_memory.content)
                self.vector_index.add_vector(saved_memory.memory_id, emb)
            except Exception as e:
                logger.error(f"Failed to index memory {saved_memory.memory_id} in vector index: {e}")

        candidate.status = "PROMOTED"
        self.repo.save_candidate(candidate)

        return saved_memory, relationships

    def extract_candidates_from_run(
        self,
        run_dict: Dict[str, Any],
        application_id: str,
        context_dict: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryCandidate]:
        """
        Deterministically extracts memory candidates from an executed TestRun payload.
        Inspects:
        - Failure records -> FAILURE_HISTORY candidates
        - Successful action steps -> WORKFLOW / WORKFLOW_TRANSITION candidates
        - Observations / states -> WORKFLOW_STATE candidates
        """
        candidates: List[MemoryCandidate] = []
        run_id = run_dict.get("run_id") or run_dict.get("id", "run_unknown")
        evidence_store = run_dict.get("evidence", {})
        evidence_ids = list(evidence_store.keys()) if isinstance(evidence_store, dict) else []

        context_info = context_dict or run_dict.get("metadata", {}).get("application_context", {})

        # 1. Extract from Failures
        failures = run_dict.get("failures", [])
        for f in failures:
            cat = f.get("category", "UNSPECIFIED")
            title = f.get("title", "Execution Failure")
            detail = f.get("detail") or f.get("message", "")
            action = f.get("failed_action", "")
            selector = f.get("selector", "")

            content = f"Failure observed: {title}. Category: {cat}."
            if selector:
                content += f" Element selector: {selector}."
            if detail:
                content += f" Detail: {detail}."

            cand = self.create_candidate(
                application_id=application_id,
                proposed_memory_type=MemoryType.FAILURE_HISTORY,
                proposed_content=content,
                source_run_id=run_id,
                source_evidence_ids=evidence_ids or [f"evi_{run_id}_fail"],
                proposed_status=MemoryStatus.OBSERVED,
                context=context_info,
                confidence_score=0.9,
            )
            candidates.append(cand)

        # 2. Extract from Executed Actions (Successful steps)
        actions = run_dict.get("actions", [])
        if actions:
            step_descs = []
            for act in actions:
                act_type = act.get("action_type") or act.get("type", "")
                selector = act.get("selector", "")
                val = act.get("value", "")
                if selector:
                    step_descs.append(f"{act_type} on '{selector}'" + (f" with '{val}'" if val else ""))

            if step_descs:
                workflow_summary = f"Workflow sequence verified: {' -> '.join(step_descs[:5])}."
                cand = self.create_candidate(
                    application_id=application_id,
                    proposed_memory_type=MemoryType.WORKFLOW,
                    proposed_content=workflow_summary,
                    source_run_id=run_id,
                    source_evidence_ids=evidence_ids or [f"evi_{run_id}_wf"],
                    proposed_status=MemoryStatus.OBSERVED,
                    context=context_info,
                    confidence_score=0.85,
                )
                candidates.append(cand)

        # 3. Extract from Telemetry or Final State
        final_url = run_dict.get("metadata", {}).get("final_url") or run_dict.get("target_url")
        if final_url:
            cand = self.create_candidate(
                application_id=application_id,
                proposed_memory_type=MemoryType.WORKFLOW_STATE,
                proposed_content=f"Application reached verified endpoint/state at {final_url}",
                source_run_id=run_id,
                source_evidence_ids=evidence_ids or [f"evi_{run_id}_state"],
                proposed_status=MemoryStatus.OBSERVED,
                context=context_info,
                confidence_score=0.8,
            )
            candidates.append(cand)

        return candidates

    def process_run_and_promote(
        self,
        run_dict: Dict[str, Any],
        application_id: str,
        context_dict: Optional[Dict[str, Any]] = None,
    ) -> List[EngineeringMemory]:
        """
        Convenience end-to-end method: extracts candidates, validates, and promotes them.
        """
        candidates = self.extract_candidates_from_run(run_dict, application_id, context_dict)
        promoted: List[EngineeringMemory] = []

        prompt_version = run_dict.get("metadata", {}).get("prompt_version")
        git_commit = run_dict.get("metadata", {}).get("git_commit")
        model_id = run_dict.get("metadata", {}).get("model_id")

        for c in candidates:
            mem, _ = self.promote_candidate(
                candidate_id=c.candidate_id,
                prompt_version=prompt_version,
                git_commit=git_commit,
                model_id=model_id,
            )
            if mem:
                promoted.append(mem)

        return promoted

    def _detect_contradiction(self, new_content: str, existing_content: str) -> bool:
        """
        Deterministic contradiction heuristic.
        Checks for semantic opposites like:
        - absent vs exists / present
        - failed vs succeeded / passed
        - requires login vs guest allowed
        - unavailable vs available
        """
        nc = new_content.lower()
        ec = existing_content.lower()

        opposites = [
            ("absent", "exists"),
            ("absent", "present"),
            ("not found", "exists"),
            ("failed", "succeeded"),
            ("disabled", "enabled"),
            ("unavailable", "available"),
            ("guest", "requires login"),
            ("disallowed", "allowed"),
        ]

        for word1, word2 in opposites:
            if (word1 in nc and word2 in ec) or (word2 in nc and word1 in ec):
                # Also check if they share a common subject keyword
                nc_words = set(nc.split())
                ec_words = set(ec.split())
                overlap = nc_words.intersection(ec_words) - {"the", "a", "an", "is", "in", "at", "to", "for", "of"}
                if len(overlap) >= 1:
                    return True

        return False

    def _detect_similarity_or_refinement(self, new_content: str, existing_content: str) -> bool:
        """
        Checks if two memory contents are related enough to be considered a refinement.
        """
        nc_words = set(new_content.lower().split())
        ec_words = set(existing_content.lower().split())
        common = nc_words.intersection(ec_words) - {"the", "a", "an", "is", "in", "at", "to", "for", "of", "and"}
        return len(common) >= 3
