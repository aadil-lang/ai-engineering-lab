"""
Pydantic schemas for Slice 8K Change Impact & Adaptive Regression MCP Tools.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.change_impact.models import (
    ChangeImpact,
    AdaptiveRegressionPlan,
    BehavioralComparison,
    RegressionFinding,
)


class AnalyzeChangeImpactRequest(BaseModel):
    repository: Optional[str] = Field(None, description="Repository name or path")
    base_commit: str = Field(..., description="Base git commit SHA")
    candidate_commit: str = Field(..., description="Candidate git commit SHA")
    changed_files: List[str] = Field(default_factory=list, description="List of modified or added files")
    changed_prompts: List[str] = Field(default_factory=list, description="List of modified prompt IDs or versions")
    changed_models: List[str] = Field(default_factory=list, description="List of modified model names or configs")
    changed_retrieval: List[str] = Field(default_factory=list, description="List of modified retrieval configs")
    changed_tools: List[str] = Field(default_factory=list, description="List of modified tools")
    changed_configuration: Dict[str, Any] = Field(default_factory=dict, description="Configuration changes")
    application_id: Optional[str] = Field(None, description="Target application ID")


class AnalyzeChangeImpactResponse(BaseModel):
    change_set_id: str
    impact: ChangeImpact


class GetChangeImpactRequest(BaseModel):
    change_set_id: str = Field(..., description="ChangeSet ID to retrieve impact graph for")


class GetChangeImpactResponse(BaseModel):
    impact: Optional[ChangeImpact] = None


class CreateRegressionPlanRequest(BaseModel):
    change_set_id: str = Field(..., description="ChangeSet ID to build plan for")
    target_id: str = Field(..., description="Target execution ID")
    application_id: Optional[str] = Field(None, description="Target application ID")
    budget: Optional[Dict[str, Any]] = Field(None, description="Step and timeout budget")


class CreateRegressionPlanResponse(BaseModel):
    plan: AdaptiveRegressionPlan


class GetRegressionPlanRequest(BaseModel):
    plan_id: str = Field(..., description="AdaptiveRegressionPlan ID to retrieve")


class GetRegressionPlanResponse(BaseModel):
    plan: Optional[AdaptiveRegressionPlan] = None


class ExecuteRegressionPlanRequest(BaseModel):
    plan_id: str = Field(..., description="AdaptiveRegressionPlan ID to execute")
    candidate_commit: Optional[str] = Field(None, description="Candidate commit SHA to verify against plan freshness")


class ExecuteRegressionPlanResponse(BaseModel):
    plan_id: str
    status: str
    executed_items: int
    scope_summary: Dict[str, int]


class GetRegressionFindingsRequest(BaseModel):
    plan_id: str = Field(..., description="AdaptiveRegressionPlan ID to retrieve findings for")


class GetRegressionFindingsResponse(BaseModel):
    plan_id: str
    findings: List[RegressionFinding]


class CompareChangeBehaviorRequest(BaseModel):
    plan_id: str = Field(..., description="AdaptiveRegressionPlan ID")
    baseline_run_id: str = Field(..., description="Run ID of the baseline execution")
    candidate_run_id: str = Field(..., description="Run ID of the candidate execution (must be distinct from baseline)")
    baseline_results: Dict[str, Any] = Field(default_factory=dict, description="Baseline test results")
    candidate_results: Dict[str, Any] = Field(default_factory=dict, description="Candidate test results")
    contract_evaluations: Optional[Dict[str, bool]] = Field(default_factory=dict, description="Evaluated behavioral contracts")
    evidence_ids: Optional[List[str]] = Field(default_factory=list, description="Collected evidence IDs")


class CompareChangeBehaviorResponse(BaseModel):
    comparison: BehavioralComparison
