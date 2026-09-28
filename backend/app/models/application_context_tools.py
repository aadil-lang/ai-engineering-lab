from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.app.prompt_lab.application_context_models import (
    AIApplicationManifest,
    EvaluationContext,
    ContextProvenance,
    ContextDifference,
)


# 1. get_application_manifest
class GetApplicationManifestRequest(BaseModel):
    application_id: str = Field(description="Unique application ID")


class GetApplicationManifestResponse(BaseModel):
    manifest: AIApplicationManifest


# 2. get_evaluation_context
class GetEvaluationContextRequest(BaseModel):
    context_id: str = Field(description="Unique evaluation context ID")


class GetEvaluationContextResponse(BaseModel):
    context: EvaluationContext


# 3. validate_evaluation_context
class ValidateEvaluationContextRequest(BaseModel):
    context_id: str = Field(description="Evaluation context ID to validate")
    require_frozen: bool = Field(default=False, description="Whether the context must be frozen")


class ValidateEvaluationContextResponse(BaseModel):
    is_valid: bool
    context_id: str
    context_hash: str
    validation_status: str = "VALID"
    message: str = "Context is structurally valid and untampered."


# 4. get_context_provenance
class GetContextProvenanceRequest(BaseModel):
    context_id: str = Field(description="Unique evaluation context ID")


class GetContextProvenanceResponse(BaseModel):
    context_id: str
    provenance: List[ContextProvenance]


# 5. compare_evaluation_contexts
class CompareEvaluationContextsRequest(BaseModel):
    context_id_a: str = Field(description="Baseline context ID")
    context_id_b: str = Field(description="Candidate context ID")


class CompareEvaluationContextsResponse(BaseModel):
    difference: ContextDifference
