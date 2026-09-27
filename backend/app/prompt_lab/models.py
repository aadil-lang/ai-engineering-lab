from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PromptStatus(str, Enum):
    DRAFT = "DRAFT"
    CANDIDATE = "CANDIDATE"
    EVALUATING = "EVALUATING"
    PASSED = "PASSED"
    DEPLOYED = "DEPLOYED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class EvaluationStrategy(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    JSON_SCHEMA = "JSON_SCHEMA"
    RULE_BASED = "RULE_BASED"
    CODE_EXECUTION = "CODE_EXECUTION"
    SQL_EXECUTION = "SQL_EXECUTION"
    GROUNDING = "GROUNDING"
    SEMANTIC_JUDGE = "SEMANTIC_JUDGE"
    LLM_AS_JUDGE = "LLM_AS_JUDGE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPOSITE = "COMPOSITE"


class EvaluationCategory(str, Enum):
    NORMAL = "NORMAL"
    AMBIGUOUS = "AMBIGUOUS"
    MISSING_INPUT = "MISSING_INPUT"
    CONTRADICTORY = "CONTRADICTORY"
    LONG_CONTEXT = "LONG_CONTEXT"
    INJECTION = "INJECTION"
    MALFORMED = "MALFORMED"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
    BOUNDARY = "BOUNDARY"
    CONFLICTING_EXAMPLES = "CONFLICTING_EXAMPLES"
    REGRESSION = "REGRESSION"


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    ABSTAINED = "ABSTAINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class GroundingStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNKNOWN = "UNKNOWN"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FailureCause(str, Enum):
    PROMPT_DEFECT = "PROMPT_DEFECT"
    MODEL_BEHAVIOR = "MODEL_BEHAVIOR"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    TOOL_FAILURE = "TOOL_FAILURE"
    APPLICATION_LOGIC = "APPLICATION_LOGIC"
    PARSER_FAILURE = "PARSER_FAILURE"
    SCHEMA_FAILURE = "SCHEMA_FAILURE"
    DATA_FAILURE = "DATA_FAILURE"
    EVALUATOR_FAILURE = "EVALUATOR_FAILURE"
    UNKNOWN = "UNKNOWN"


class EpistemicType(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"


class CandidateStatus(str, Enum):
    PROPOSED = "PROPOSED"
    EVALUATING = "EVALUATING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class CaseTransition(str, Enum):
    NEW_PASS = "NEW_PASS"
    NEW_FAILURE = "NEW_FAILURE"
    REGRESSION = "REGRESSION"
    FIXED_FAILURE = "FIXED_FAILURE"
    UNCHANGED = "UNCHANGED"


# 1. Prompt Models
class StructuredPromptComponents(BaseModel):
    role: Optional[str] = None
    objective: Optional[str] = None
    context: Optional[str] = None
    instructions: Optional[List[str]] = Field(default_factory=list)
    constraints: Optional[List[str]] = Field(default_factory=list)
    examples: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    failure_handling: Optional[str] = None
    tool_rules: Optional[List[str]] = Field(default_factory=list)
    validation_rules: Optional[List[str]] = Field(default_factory=list)


class PromptDefinition(BaseModel):
    prompt_id: str = Field(description="Unique immutable prompt identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptVersion(BaseModel):
    prompt_id: str
    version: int = Field(ge=1, description="Sequential version number")
    template: str = Field(description="Raw template string with placeholders, e.g. {{query}}")
    variables_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema describing expected variables")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="Expected JSON output schema if structured")
    components: Optional[StructuredPromptComponents] = Field(default=None, description="Optional structured prompt sections")
    parent_version: Optional[int] = None
    change_reason: Optional[str] = None
    status: PromptStatus = PromptStatus.DRAFT
    is_evaluated: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 2. Evaluation Suite & Cases
class EvaluationCase(BaseModel):
    case_id: str = Field(description="Unique case identifier")
    input: Dict[str, Any] = Field(description="Input variables mapping to prompt template")
    expected_behavior: str = Field(description="Human-readable statement of expected behavior")
    expected_output: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="Optional exact output or structure")
    constraints: List[str] = Field(default_factory=list, description="Rules: e.g. required_fields, forbidden_phrases")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved context chunks for grounding")
    tools: List[str] = Field(default_factory=list, description="Expected tool names or permissions")
    evaluation_strategy: EvaluationStrategy = EvaluationStrategy.COMPOSITE
    severity: SeverityLevel = SeverityLevel.MEDIUM
    tags: List[str] = Field(default_factory=list)
    category: EvaluationCategory = EvaluationCategory.NORMAL


class EvaluationSuite(BaseModel):
    suite_id: str
    name: str
    description: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EvaluationSuiteVersion(BaseModel):
    suite_id: str
    version: int = Field(ge=1)
    description: str = ""
    cases: List[EvaluationCase] = Field(default_factory=list)
    is_frozen: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 3. AI Execution Record
class AIExecutionRecord(BaseModel):
    execution_id: str
    evaluation_run_id: str
    evaluation_case_id: str
    prompt_id: str
    prompt_version: int
    model: str
    model_version: Optional[str] = None
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    rendered_prompt_hash: str
    output_hash: str
    rendered_prompt: str
    raw_output: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0
    tool_usage: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_usage: List[Dict[str, Any]] = Field(default_factory=list)
    application_version: Optional[str] = None
    git_commit_sha: Optional[str] = None


# 4. Evaluator Results
class GroundingClaimResult(BaseModel):
    claim_text: str
    status: GroundingStatus
    supporting_source_ids: List[str] = Field(default_factory=list)
    contradicting_source_ids: List[str] = Field(default_factory=list)
    rationale: str = ""


class EvaluatorResult(BaseModel):
    evaluator_name: str
    strategy: EvaluationStrategy
    status: EvaluationStatus
    score: Optional[float] = None
    confidence: Optional[float] = None
    rationale: str = ""
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    claims: List[GroundingClaimResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CaseEvaluationResult(BaseModel):
    case_id: str
    category: EvaluationCategory
    severity: SeverityLevel
    overall_status: EvaluationStatus
    evaluator_results: List[EvaluatorResult] = Field(default_factory=list)
    failure_causes: List[FailureCause] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    execution: Optional[AIExecutionRecord] = None
    confidence: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 5. Diagnostic Models
class DiagnosticFact(BaseModel):
    epistemic_type: EpistemicType
    statement: str
    evidence_refs: List[str] = Field(default_factory=list)


class PromptDiagnosis(BaseModel):
    diagnosis_id: str
    evaluation_run_id: str
    case_id: str
    primary_cause: FailureCause
    confidence: float = Field(ge=0.0, le=1.0)
    facts: List[DiagnosticFact] = Field(default_factory=list)
    observed_summary: str
    inferred_summary: str
    hypothesis_summary: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptImprovementCandidate(BaseModel):
    candidate_id: str
    source_prompt_version: int
    proposed_template: str
    proposed_components: Optional[StructuredPromptComponents] = None
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    diagnosis_ids: List[str] = Field(default_factory=list)
    status: CandidateStatus = CandidateStatus.PROPOSED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# 6. Evaluation Run
class EvaluationRun(BaseModel):
    evaluation_run_id: str
    prompt_id: str
    prompt_version: int
    suite_id: str
    suite_version: int
    model: str
    generation_parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "COMPLETED"  # RUNNING, COMPLETED, FAILED
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    partial_cases: int = 0
    unknown_cases: int = 0
    abstained_cases: int = 0
    pass_rate: float = 0.0
    case_results: List[CaseEvaluationResult] = Field(default_factory=list)
    diagnoses: List[PromptDiagnosis] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    duration_ms: int = 0


# 7. Comparison & Regressions
class CaseTransitionRecord(BaseModel):
    case_id: str
    category: EvaluationCategory
    severity: SeverityLevel
    status_v1: EvaluationStatus
    status_v2: EvaluationStatus
    transition: CaseTransition
    rationale_diff: str = ""


class PromptComparisonResult(BaseModel):
    prompt_id: str
    v1_version: int
    v2_version: int
    suite_id: str
    suite_version: int
    v1_run_id: str
    v2_run_id: str
    v1_pass_rate: float
    v2_pass_rate: float
    pass_rate_delta: float
    total_cases: int
    regressions_count: int
    fixed_failures_count: int
    unchanged_count: int
    new_passes_count: int
    new_failures_count: int
    critical_regressions: List[CaseTransitionRecord] = Field(default_factory=list)
    transitions: List[CaseTransitionRecord] = Field(default_factory=list)
    deterministic_pass_rates: Dict[str, float] = Field(default_factory=dict)
    grounding_pass_rates: Dict[str, float] = Field(default_factory=dict)
    semantic_pass_rates: Dict[str, float] = Field(default_factory=dict)


# 8. Immutable Evaluation Snapshot
class EvaluationSnapshot(BaseModel):
    snapshot_id: str
    protocol_version: str = "PromptEvaluationProtocol v1.0"
    prompt_id: str
    prompt_version: int
    suite_id: str
    suite_version: int
    model: str
    model_parameters: Dict[str, Any] = Field(default_factory=dict)
    dataset_provenance: Dict[str, Any] = Field(default_factory=dict)
    evaluation_run_id: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float
    evaluator_versions: Dict[str, str] = Field(default_factory=dict)
    sha256_hash: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
