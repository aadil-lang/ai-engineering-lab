"""
Slice 8C — Context-Aware Autonomous Dogfooding Models

These models bind dogfooding runs to frozen AI Application Contexts,
enable runtime verification, and track the complete provenance chain
from failure through diagnosis, proposal, authorization, and retest.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import hashlib
import json

from backend.app.models.enums import (
    CausalLayer,
    RetestTransition,
    ContractStatus,
    ContextVerificationStatus,
)
from backend.app.prompt_lab.application_context_models import EpistemicStatus


class ComponentVerification(BaseModel):
    """Runtime verification result for a single context component."""
    component: str  # e.g. "prompt", "model", "git_commit", "retrieval", "tools", "parser"
    status: ContextVerificationStatus = ContextVerificationStatus.UNAVAILABLE
    epistemic_status: EpistemicStatus = EpistemicStatus.DECLARED
    declared_value: Optional[str] = None
    observed_value: Optional[str] = None
    mismatch_detail: Optional[str] = None


class DogfoodingRunContext(BaseModel):
    """
    Binds a dogfooding TestRun to the frozen AI Application Context.
    Preserves exact provenance of each context component.
    """
    context_binding_id: str = Field(default_factory=lambda: f"dfctx_{uuid.uuid4().hex[:8]}")
    run_id: str
    evaluation_context_id: str
    context_hash: str

    # Application identity
    application_id: str
    feature_id: str

    # Version provenance
    git_commit_sha: Optional[str] = None

    # Prompt provenance
    prompt_id: str
    prompt_version: int

    # Model provenance
    model: str
    model_version: Optional[str] = None

    # Configuration hashes (references, not full configs)
    retrieval_configuration_hash: Optional[str] = None
    tool_configuration_hash: Optional[str] = None
    parser_configuration_hash: Optional[str] = None

    # Behavioral contracts
    behavioral_contract_ids: List[str] = Field(default_factory=list)

    # Evaluation case
    evaluation_case_id: Optional[str] = None

    # Runtime verification results
    component_verifications: List[ComponentVerification] = Field(default_factory=list)

    # AI feature detection
    ai_feature_detected: bool = False

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_context_valid(self) -> bool:
        """Context is valid if no MISMATCH was detected."""
        return not any(
            v.status == ContextVerificationStatus.MISMATCH
            for v in self.component_verifications
        )


class AIContextEvidence(BaseModel):
    """
    AI-context evidence collected during a dogfooding run.
    Supplements the existing Slice 8B evidence (DOM, screenshot, console, network).
    """
    evidence_id: str = Field(default_factory=lambda: f"aictx_{uuid.uuid4().hex[:8]}")
    run_id: str
    prompt_version: Optional[int] = None
    model: Optional[str] = None
    model_version: Optional[str] = None
    rendered_input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    retrieval_evidence_refs: List[str] = Field(default_factory=list)
    tool_invocation_refs: List[str] = Field(default_factory=list)
    parser_result: Optional[Dict[str, Any]] = None
    behavioral_contract_id: Optional[str] = None
    evaluation_case_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CausalClassification(BaseModel):
    """
    Evidence-backed causal layer classification for an AI failure.
    Supports multiple layers when evidence indicates multiple contributors.
    """
    classification_id: str = Field(default_factory=lambda: f"ccls_{uuid.uuid4().hex[:8]}")
    diagnosis_id: str
    run_id: str

    primary_layer: CausalLayer
    primary_evidence_refs: List[str] = Field(default_factory=list)
    primary_epistemic_status: EpistemicStatus = EpistemicStatus.HYPOTHESIS

    secondary_layers: List[CausalLayer] = Field(default_factory=list)
    secondary_evidence_refs: List[str] = Field(default_factory=list)

    rationale: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptImprovementCandidate(BaseModel):
    """
    Prompt change candidate derived from dogfooding evidence and diagnosis.
    This is a proposal only — no automatic production mutation.
    """
    candidate_id: str = Field(default_factory=lambda: f"pic_{uuid.uuid4().hex[:8]}")

    # Application identity
    application_id: str
    feature_id: str

    # Source context provenance
    source_context_id: str
    source_context_hash: str
    source_git_commit_sha: Optional[str] = None

    # Source prompt
    source_prompt_id: str
    source_prompt_version: int

    # Evidence chain
    diagnosis_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)

    # Affected contracts
    affected_behavioral_contract_ids: List[str] = Field(default_factory=list)

    # Proposed change
    proposed_prompt_change: str
    rationale: str

    # Status
    status: str = "PROPOSED"  # PROPOSED | EVALUATING | ACCEPTED | REJECTED

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RetestComparison(BaseModel):
    """
    Explicit comparison of what changed between baseline and candidate contexts.
    """
    dimension: str  # e.g. "prompt", "model", "git_commit", etc.
    baseline_value: Optional[str] = None
    candidate_value: Optional[str] = None
    status: str = "SAME"  # SAME | CHANGED


class RetestResult(BaseModel):
    """
    Comparison of baseline vs. candidate dogfooding runs.
    Detects regressions, fixed failures, and multi-variable changes.
    """
    retest_id: str = Field(default_factory=lambda: f"rt_{uuid.uuid4().hex[:8]}")

    # Run references
    baseline_run_id: str
    candidate_run_id: str

    # Context references
    baseline_context_id: str
    candidate_context_id: str

    # Per-check transitions
    transitions: Dict[str, RetestTransition] = Field(default_factory=dict)

    # Per-contract evaluations
    contract_evaluations: Dict[str, ContractStatus] = Field(default_factory=dict)

    # Context difference analysis
    comparisons: List[RetestComparison] = Field(default_factory=list)
    changed_dimensions: List[str] = Field(default_factory=list)
    is_multi_variable_change: bool = False

    # Verification status
    is_independently_verified: bool = False
    has_regressions: bool = False

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def compute_config_hash(config: Optional[Dict[str, Any]]) -> Optional[str]:
    """Compute SHA-256 hash for a configuration dictionary."""
    if config is None:
        return None
    raw = json.dumps(config, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
