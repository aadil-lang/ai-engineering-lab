from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    EvaluationSuite,
    EvaluationSuiteVersion,
    EvaluationRun,
    CaseEvaluationResult,
    PromptDiagnosis,
    PromptComparisonResult,
    CaseTransitionRecord,
    EvaluationSnapshot,
    StructuredPromptComponents,
)


# 1. list_prompts
class ListPromptsRequest(BaseModel):
    limit: Optional[int] = Field(default=50, description="Max prompts to list")


class ListPromptsResponse(BaseModel):
    prompts: List[PromptDefinition]


# 2. get_prompt
class GetPromptRequest(BaseModel):
    prompt_id: str = Field(description="Unique prompt ID")


class GetPromptResponse(BaseModel):
    prompt: PromptDefinition
    versions: List[PromptVersion] = Field(default_factory=list)


# 3. get_prompt_version
class GetPromptVersionRequest(BaseModel):
    prompt_id: str = Field(description="Prompt identifier")
    version: int = Field(description="Version number")


class GetPromptVersionResponse(BaseModel):
    version: PromptVersion


# 4. create_prompt_version
class CreatePromptVersionRequest(BaseModel):
    prompt_id: str
    template: str
    variables_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    components: Optional[StructuredPromptComponents] = None
    change_reason: Optional[str] = None
    parent_version: Optional[int] = None
    status: PromptStatus = PromptStatus.DRAFT


class CreatePromptVersionResponse(BaseModel):
    version: PromptVersion


# 5. list_evaluation_suites
class ListEvaluationSuitesRequest(BaseModel):
    limit: Optional[int] = Field(default=50)


class ListEvaluationSuitesResponse(BaseModel):
    suites: List[EvaluationSuite]


# 6. get_evaluation_suite
class GetEvaluationSuiteRequest(BaseModel):
    suite_id: str
    version: Optional[int] = Field(default=None, description="Optional version, defaults to latest")


class GetEvaluationSuiteResponse(BaseModel):
    suite: EvaluationSuite
    suite_version: Optional[EvaluationSuiteVersion] = None


# 7. start_evaluation
class StartEvaluationRequest(BaseModel):
    prompt_id: str
    prompt_version: int
    suite_id: str
    suite_version: int
    model: str = "mock-agent-v1"
    generation_parameters: Optional[Dict[str, Any]] = None


class StartEvaluationResponse(BaseModel):
    run: EvaluationRun
    snapshot: Optional[EvaluationSnapshot] = None


# 8. get_evaluation
class GetEvaluationRequest(BaseModel):
    evaluation_run_id: str


class GetEvaluationResponse(BaseModel):
    run: EvaluationRun
    diagnoses: List[PromptDiagnosis] = Field(default_factory=list)


# 9. get_evaluation_result
class GetEvaluationResultRequest(BaseModel):
    evaluation_run_id: str
    case_id: str


class GetEvaluationResultResponse(BaseModel):
    case_result: Optional[CaseEvaluationResult] = None
    diagnosis: Optional[PromptDiagnosis] = None


# 10. compare_prompt_versions
class ComparePromptVersionsRequest(BaseModel):
    prompt_id: str
    v1_version: int
    v2_version: int
    suite_id: str
    suite_version: int


class ComparePromptVersionsResponse(BaseModel):
    comparison: PromptComparisonResult


# 11. get_prompt_regressions
class GetPromptRegressionsRequest(BaseModel):
    prompt_id: str
    v1_version: int
    v2_version: int
    suite_id: str
    suite_version: int


class GetPromptRegressionsResponse(BaseModel):
    prompt_id: str
    v1_version: int
    v2_version: int
    total_regressions: int
    critical_regressions: List[CaseTransitionRecord] = Field(default_factory=list)
    regressions: List[CaseTransitionRecord] = Field(default_factory=list)


# 12. get_prompt_diagnosis
class GetPromptDiagnosisRequest(BaseModel):
    diagnosis_id: str


class GetPromptDiagnosisResponse(BaseModel):
    diagnosis: PromptDiagnosis


# 13. get_prompt_evidence
class GetPromptEvidenceRequest(BaseModel):
    evaluation_run_id: str
    case_id: str


class GetPromptEvidenceResponse(BaseModel):
    case_id: str
    evidence_ids: List[str] = Field(default_factory=list)
    execution: Optional[Any] = None
    facts: List[Dict[str, Any]] = Field(default_factory=list)
