"""
Slice 8E — Memory MCP Tool Request and Response Models.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.app.memory.models import (
    EngineeringMemory,
    MemorySearchResult,
)


class SearchEngineeringMemoryRequest(BaseModel):
    query: str
    application_id: Optional[str] = None
    target_id: Optional[str] = None
    component_id: Optional[str] = None
    workflow_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)
    current_prompt_version: Optional[str] = None
    current_git_commit: Optional[str] = None
    semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class SearchEngineeringMemoryResponse(BaseModel):
    results: List[MemorySearchResult]
    total_found: int


class GetEngineeringMemoryRequest(BaseModel):
    memory_id: str


class GetEngineeringMemoryResponse(BaseModel):
    memory: Optional[EngineeringMemory] = None


class GetMemoryEvidenceRequest(BaseModel):
    memory_id: str


class GetMemoryEvidenceResponse(BaseModel):
    memory_id: str
    source_type: str
    source_run_id: str
    source_evidence_ids: List[str]
    source_diagnosis_id: Optional[str] = None
    context_id: Optional[str] = None
    context_hash: Optional[str] = None
    git_commit: Optional[str] = None
    prompt_version: Optional[str] = None


class GetMemoryHistoryRequest(BaseModel):
    memory_id: str


class GetMemoryHistoryResponse(BaseModel):
    memory_id: str
    audit_logs: List[Dict[str, Any]]
