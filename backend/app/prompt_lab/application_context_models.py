from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from backend.app.prompt_lab.models import CandidateStatus


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    DECLARED = "DECLARED"
    HYPOTHESIS = "HYPOTHESIS"


class EvaluationMode(str, Enum):
    PROMPT_LEVEL = "PROMPT_LEVEL"
    APPLICATION_LEVEL = "APPLICATION_LEVEL"


class ContractEvaluationStatus(str, Enum):
    CONTRACT_PRESERVED = "CONTRACT_PRESERVED"
    CONTRACT_VIOLATED = "CONTRACT_VIOLATED"
    CONTRACT_UNCERTAIN = "CONTRACT_UNCERTAIN"


class ContextProvenance(BaseModel):
    """
    Provenance record for an individual context component.
    Epistemic distinction ensures DECLARED config is never silently treated as OBSERVED truth.
    """
    component: str = Field(description="Component name: prompt, git_commit, model, tools, retrieval, parser, behavioral_contract, evaluation_suite")
    source: str = Field(description="Source system: PromptRegistry, GitHub, ApplicationConfig, ToolRegistry, EvaluationRegistry")
    source_id: str = Field(description="Identifier within source system")
    source_version: Optional[str] = Field(default=None, description="Version or commit hash")
    epistemic_status: EpistemicStatus = Field(default=EpistemicStatus.DECLARED)
    observed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hash: Optional[str] = Field(default=None, description="Cryptographic SHA-256 of the component configuration or content")


class AIApplicationManifest(BaseModel):
    """
    Contract declaring the application, feature, prompt, model, schemas,
    retrieval, tools, parser, behavioral contracts, and evaluation suites.
    """
    application_id: str
    feature_id: str
    application_name: str
    application_version: str
    git_repository: Optional[str] = None
    git_commit_sha: Optional[str] = None
    prompt_id: str
    prompt_version: int
    model: str
    model_version: Optional[str] = None
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    retrieval_configuration: Optional[Dict[str, Any]] = None
    tool_configuration: Optional[Dict[str, Any]] = None
    parser_configuration: Optional[Dict[str, Any]] = None
    application_configuration: Dict[str, Any] = Field(default_factory=dict)
    behavioral_contract_ids: List[str] = Field(default_factory=list)
    evaluation_suite_ids: List[str] = Field(default_factory=list)
    environment: str = "staging"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvaluationContext(BaseModel):
    """
    Frozen execution and evaluation context binding the prompt to the real application.
    Immutable once evaluation begins.
    """
    context_id: str
    application_id: str
    feature_id: str
    application_version: str
    git_commit_sha: Optional[str] = None
    prompt_id: str
    prompt_version: int
    model: str
    model_version: Optional[str] = None
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    retrieval_configuration: Optional[Dict[str, Any]] = None
    tool_configuration: Optional[Dict[str, Any]] = None
    parser_configuration: Optional[Dict[str, Any]] = None
    application_configuration: Dict[str, Any] = Field(default_factory=dict)
    behavioral_contract_ids: List[str] = Field(default_factory=list)
    evaluation_suite_ids: List[str] = Field(default_factory=list)
    provenance: List[ContextProvenance] = Field(default_factory=list)
    is_frozen: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context_hash: str = ""


class ContextBinding(BaseModel):
    """
    Explicit recorded binding between an application feature and prompt/model/tooling.
    Distinguishes runtime-verified OBSERVED from purely DECLARED binding.
    """
    binding_id: Optional[str] = None
    application_id: str
    feature_id: str
    prompt_id: str
    prompt_version: int
    model: str
    model_version: Optional[str] = None
    retrieval_configuration: Optional[Dict[str, Any]] = None
    tool_configuration: Optional[Dict[str, Any]] = None
    parser_configuration: Optional[Dict[str, Any]] = None
    evaluation_suite_id: str
    verified_at_runtime: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.DECLARED
    bound_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContextDifference(BaseModel):
    """
    Multi-dimensional difference analysis between baseline and candidate evaluation contexts.
    Detects MULTI_VARIABLE_CHANGE to prevent unsupported causal attribution to prompt changes.
    """
    context_id_a: str
    context_id_b: str
    dimensions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    changed_dimensions: List[str] = Field(default_factory=list)
    is_multi_variable_change: bool = False
    can_attribute_to_prompt: bool = True
    attribution_note: str = ""


class EvaluationContextSnapshot(BaseModel):
    """
    Immutable, cryptographically hashed snapshot of an application-level evaluation run.
    """
    snapshot_id: str
    protocol_version: str = "AIApplicationContextProtocol v1.0"
    context_id: str
    context_hash: str
    application_id: str
    feature_id: str
    git_commit_sha: Optional[str] = None
    prompt_id: str
    prompt_version: int
    model: str
    model_version: Optional[str] = None
    retrieval_configuration: Optional[Dict[str, Any]] = None
    tool_configuration: Optional[Dict[str, Any]] = None
    parser_configuration: Optional[Dict[str, Any]] = None
    behavioral_contract_ids: List[str] = Field(default_factory=list)
    evaluation_suite_id: str
    evaluation_suite_version: int
    results: Dict[str, Any] = Field(default_factory=dict)
    contract_evaluations: Dict[str, ContractEvaluationStatus] = Field(default_factory=dict)
    evaluator_versions: Dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sha256: str = ""


class ContextAwarePromptCandidate(BaseModel):
    """
    Prompt improvement candidate tied explicitly to the application context from which it was derived.
    """
    candidate_id: str
    application_id: str
    feature_id: str
    source_context_id: str
    source_git_commit_sha: Optional[str] = None
    source_prompt_version: int
    source_evaluation_id: str
    affected_behavioral_contract_ids: List[str] = Field(default_factory=list)
    proposed_change: str
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    diagnosis_ids: List[str] = Field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
