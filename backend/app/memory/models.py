"""
Slice 8E — Application-Aware Engineering Memory Domain Models

Provides canonical structured memory models, relationship graphs, candidate
lifecycle states, and version applicability tracking for the autonomous QA platform.

Core Invariants:
1. Evidence records what happened; Memory stores validated knowledge derived from evidence.
2. Structured Engineering Memory is the canonical source of learned knowledge.
3. Current runtime evidence overrides historical memory.
4. Contradictions are preserved rather than silently overwritten.
5. All memory retrieval and reasoning remain local without external cloud APIs.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    """Deterministic classification of learned engineering knowledge."""
    APPLICATION_FACT = "APPLICATION_FACT"              # General static or verified application attribute
    WORKFLOW = "WORKFLOW"                              # High-level user journey or sequence of states
    WORKFLOW_STATE = "WORKFLOW_STATE"                  # Discrete observable state in a workflow
    WORKFLOW_TRANSITION = "WORKFLOW_TRANSITION"        # Observed transition between two workflow states
    BEHAVIORAL_OBSERVATION = "BEHAVIORAL_OBSERVATION"  # Observed dynamic UI or backend behavior
    EDGE_CASE = "EDGE_CASE"                            # Discovered boundary condition or stress point
    FAILURE_HISTORY = "FAILURE_HISTORY"                # Past failure pattern (used as test hypothesis)
    REGRESSION_HISTORY = "REGRESSION_HISTORY"          # Observed regression across versions
    CONTRACT_REFERENCE = "CONTRACT_REFERENCE"          # Binding to Slice 8C behavioral contract
    AI_BEHAVIOR = "AI_BEHAVIOR"                        # Specific LLM/generative behavior observation
    CHANGE_IMPACT = "CHANGE_IMPACT"                    # Known impact of a prompt/code change
    REMEDIATION_HISTORY = "REMEDIATION_HISTORY"        # Historical fix and verification outcome
    RELIABILITY_PATTERN = "RELIABILITY_PATTERN"        # Statistical reliability or flakiness pattern
    UNKNOWN_BEHAVIOR = "UNKNOWN_BEHAVIOR"              # Unclassified or anomalous observation


class MemoryStatus(str, Enum):
    """
    Epistemic and lifecycle status of a memory.
    Invariant: Never silently upgrade DECLARED or INFERRED to OBSERVED.
    """
    OBSERVED = "OBSERVED"        # Directly supported by runtime evidence
    DECLARED = "DECLARED"        # Supplied by manifest/context, not independently verified
    INFERRED = "INFERRED"        # Derived from evidence but not directly observed
    HISTORICAL = "HISTORICAL"    # Previously observed behavior that may or may not still apply
    STALE = "STALE"              # Previously valid memory whose applicability has expired
    INVALIDATED = "INVALIDATED"  # Explicitly contradicted by newer reliable evidence
    UNKNOWN = "UNKNOWN"          # Insufficient evidence


class MemoryApplicability(str, Enum):
    """Evaluated applicability of historical memory to a current execution context."""
    APPLICABLE = "APPLICABLE"                      # Matches current version/context dimensions
    PARTIALLY_APPLICABLE = "PARTIALLY_APPLICABLE"  # Matches application, but minor dimension changed
    STALE = "STALE"                                # Version or time threshold has expired
    INVALIDATED = "INVALIDATED"                    # Contradicted by newer runtime evidence
    UNKNOWN = "UNKNOWN"                            # Context dimensions cannot be compared


class RelationshipType(str, Enum):
    """Explicit relationship between memory units."""
    SUPPORTS = "SUPPORTS"          # Strengthens confidence in another memory
    CONTRADICTS = "CONTRADICTS"    # Directly conflicts with another memory
    SUPERSEDES = "SUPERSEDES"      # Replaces an older version of knowledge
    REFINES = "REFINES"            # Adds more granular detail to a parent memory
    DERIVED_FROM = "DERIVED_FROM"  # Built from or synthesized from another memory
    RELATED_TO = "RELATED_TO"      # Associative link across workflows or components


class MemoryRelationship(BaseModel):
    """Explicit semantic edge connecting two memory entities."""
    relationship_id: str = Field(default_factory=lambda: f"rel_{uuid.uuid4().hex[:8]}")
    source_memory_id: str
    target_memory_id: str
    relationship_type: RelationshipType
    rationale: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EngineeringMemory(BaseModel):
    """
    Canonical structured memory record.
    Preserves exact provenance back to runtime evidence and frozen AI contexts.
    """
    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    application_id: str
    target_id: Optional[str] = None
    component_id: Optional[str] = None
    workflow_id: Optional[str] = None

    memory_type: MemoryType
    content: str
    status: MemoryStatus = MemoryStatus.OBSERVED

    # Provenance links
    source_type: str = "RUN_EXECUTION"  # RUN_EXECUTION | DETERMINISTIC_EVALUATION | DIAGNOSIS | DECLARED_CONTEXT
    source_run_id: Optional[str] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    source_diagnosis_id: Optional[str] = None

    # Context compatibility references
    context_id: Optional[str] = None
    context_hash: Optional[str] = None
    git_commit: Optional[str] = None
    prompt_version: Optional[Union[str, int]] = None
    model_id: Optional[str] = None
    retrieval_version: Optional[Union[str, int]] = "1"

    # Temporal & versioning
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_verified_at: Optional[str] = None
    version: int = 1

    # Heuristics & Tags
    confidence_metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

    def evaluate_applicability(
        self,
        current_application_id: str,
        current_git_commit: Optional[str] = None,
        current_prompt_version: Optional[int] = None,
        current_model_id: Optional[str] = None,
    ) -> MemoryApplicability:
        """
        Deterministically evaluates whether this memory applies to the current execution context.
        """
        if self.application_id != current_application_id:
            return MemoryApplicability.UNKNOWN

        if self.status == MemoryStatus.INVALIDATED:
            return MemoryApplicability.INVALIDATED

        if self.status == MemoryStatus.STALE:
            return MemoryApplicability.STALE

        # Check prompt version dimension
        if self.prompt_version is not None and current_prompt_version is not None:
            if self.prompt_version != current_prompt_version:
                return MemoryApplicability.PARTIALLY_APPLICABLE

        # Check git commit dimension
        if self.git_commit and current_git_commit and self.git_commit != current_git_commit:
            return MemoryApplicability.PARTIALLY_APPLICABLE

        # Check model dimension
        if self.model_id and current_model_id and self.model_id != current_model_id:
            return MemoryApplicability.PARTIALLY_APPLICABLE

        return MemoryApplicability.APPLICABLE

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary dictionary without internal CoT, safe for API and Live Console."""
        return {
            "memory_id": self.memory_id,
            "application_id": self.application_id,
            "target_id": self.target_id,
            "component_id": self.component_id,
            "workflow_id": self.workflow_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "status": self.status.value,
            "source_run_id": self.source_run_id,
            "evidence_count": len(self.source_evidence_ids),
            "prompt_version": self.prompt_version,
            "version": self.version,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MemoryCandidate(BaseModel):
    """
    Proposed knowledge candidate derived from an execution run.
    Must undergo deterministic validation before promotion to canonical EngineeringMemory.
    """
    candidate_id: str = Field(default_factory=lambda: f"cand_{uuid.uuid4().hex[:8]}")
    application_id: str
    target_id: Optional[str] = None
    component_id: Optional[str] = None
    workflow_id: Optional[str] = None

    proposed_memory_type: MemoryType
    proposed_content: str
    proposed_status: MemoryStatus = MemoryStatus.INFERRED

    source_run_id: str
    source_evidence_ids: List[str] = Field(default_factory=list)
    source_diagnosis_id: Optional[str] = None

    context: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(default=0.7, ge=0.0, le=1.0)
    validation_rules_passed: List[str] = Field(default_factory=list)

    status: str = "PROPOSED"  # PROPOSED | VALIDATED | PROMOTED | REJECTED
    rejection_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MemorySearchResult(BaseModel):
    """Hybrid RAG retrieval result with deterministic ranking metrics and applicability."""
    memory: EngineeringMemory
    score: float
    semantic_similarity: float
    applicability: MemoryApplicability
    ranking_factors: Dict[str, float] = Field(default_factory=dict)
    conflict_notes: Optional[str] = None
