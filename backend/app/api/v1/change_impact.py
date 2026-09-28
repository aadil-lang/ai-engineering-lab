"""
Slice 8K — Change Impact & Adaptive Regression API Router

Provides REST endpoints for:
- Analyzing change impacts across code, prompt, model, and configuration
- Retrieving ChangeSets and Impact Graphs
- Generating and fetching AdaptiveRegressionPlans (DEEP, TARGETED, SMOKE)
- Executing regression suites with candidate Git SHA freshness checks
- Retrieving Behavioral Comparisons and Regression Findings
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.app.change_impact.models import (
    ChangeType,
    ChangeSource,
    ChangeSet,
    ChangeImpact,
    AdaptiveRegressionPlan,
    BehavioralComparison,
    RegressionFinding,
    RegressionPlanItem,
    RegressionScopeExpansion,
)
from backend.app.change_impact.service import ChangeImpactService
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.prompt_lab.application_context_service import ApplicationContextService

router = APIRouter()

# Shared singleton instance
_memory_repo = EngineeringMemoryRepository()
_change_impact_service = ChangeImpactService(memory_repository=_memory_repo)


def get_change_impact_service() -> ChangeImpactService:
    return _change_impact_service


class AnalyzeChangeRequest(BaseModel):
    repository: Optional[str] = None
    base_commit: str = Field(..., description="Base git commit SHA")
    candidate_commit: str = Field(..., description="Candidate git commit SHA")
    changed_files: List[str] = Field(default_factory=list)
    changed_prompts: List[str] = Field(default_factory=list)
    changed_models: List[str] = Field(default_factory=list)
    changed_retrieval: List[str] = Field(default_factory=list)
    changed_tools: List[str] = Field(default_factory=list)
    changed_configuration: Dict[str, Any] = Field(default_factory=dict)
    application_id: Optional[str] = None
    session_id: str = ""
    run_id: str = ""


class CreatePlanRequest(BaseModel):
    change_set_id: str
    target_id: str
    application_id: Optional[str] = None
    budget: Optional[Dict[str, Any]] = None
    session_id: str = ""
    run_id: str = ""


class ExecutePlanRequest(BaseModel):
    candidate_commit: Optional[str] = None
    session_id: str = ""
    run_id: str = ""


class CompareRunsRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str
    baseline_results: Dict[str, Any] = Field(default_factory=dict)
    candidate_results: Dict[str, Any] = Field(default_factory=dict)
    contract_evaluations: Optional[Dict[str, bool]] = Field(default_factory=dict)
    evidence_ids: Optional[List[str]] = Field(default_factory=list)
    session_id: str = ""


# ============================================================================
# Change Analysis Endpoints
# ============================================================================

@router.post("/change-impact/analyze", response_model=ChangeImpact)
def analyze_change(
    req: AnalyzeChangeRequest,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Analyzes a proposed ChangeSet and builds the directed Impact Graph."""
    cs = ChangeSet(
        repository=req.repository,
        base_commit=req.base_commit,
        candidate_commit=req.candidate_commit,
        changed_files=req.changed_files,
        changed_prompts=req.changed_prompts,
        changed_models=req.changed_models,
        changed_retrieval=req.changed_retrieval,
        changed_tools=req.changed_tools,
        changed_configuration=req.changed_configuration,
    )
    impact = service.analyze_change(
        cs,
        application_id=req.application_id,
        session_id=req.session_id,
        run_id=req.run_id
    )
    return impact


@router.get("/change-impact/{change_set_id}", response_model=ChangeSet)
def get_change_set(
    change_set_id: str,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Retrieves a ChangeSet by its ID."""
    cs = service.get_change_set(change_set_id)
    if not cs:
        raise HTTPException(status_code=404, detail=f"ChangeSet '{change_set_id}' not found.")
    return cs


@router.get("/change-impact/{change_set_id}/graph", response_model=ChangeImpact)
def get_impact_graph(
    change_set_id: str,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Retrieves the complete Impact Graph and affected components/workflows."""
    impact = service.get_impact(change_set_id)
    if not impact:
        raise HTTPException(status_code=404, detail=f"Impact for ChangeSet '{change_set_id}' not found.")
    return impact


# ============================================================================
# Regression Plan Endpoints
# ============================================================================

@router.post("/regression/plans", response_model=AdaptiveRegressionPlan)
def create_regression_plan(
    req: CreatePlanRequest,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Formulates a new AdaptiveRegressionPlan."""
    try:
        plan = service.create_regression_plan(
            change_set_id=req.change_set_id,
            target_id=req.target_id,
            application_id=req.application_id,
            budget=req.budget,
            session_id=req.session_id,
            run_id=req.run_id
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/regression/plans/{plan_id}", response_model=AdaptiveRegressionPlan)
def get_regression_plan(
    plan_id: str,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Retrieves an AdaptiveRegressionPlan by ID."""
    plan = service.get_regression_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found.")
    return plan


@router.post("/regression/plans/{plan_id}/execute")
def execute_regression_plan(
    plan_id: str,
    req: ExecutePlanRequest,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Executes a planned regression suite while verifying candidate commit freshness."""
    try:
        res = service.execute_regression_plan(
            plan_id=plan_id,
            candidate_commit=req.candidate_commit,
            session_id=req.session_id,
            run_id=req.run_id
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/regression/plans/{plan_id}/findings", response_model=List[RegressionFinding])
def get_regression_findings(
    plan_id: str,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Retrieves detected regression findings for a plan."""
    return service.get_findings(plan_id)


@router.get("/regression/plans/{plan_id}/comparison", response_model=Optional[BehavioralComparison])
def get_regression_comparison(
    plan_id: str,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Retrieves the behavioral comparison for a plan."""
    comp = service.get_comparison(plan_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Comparison for plan '{plan_id}' not found.")
    return comp


@router.post("/regression/plans/{plan_id}/compare", response_model=BehavioralComparison)
def compare_plan_runs(
    plan_id: str,
    req: CompareRunsRequest,
    service: ChangeImpactService = Depends(get_change_impact_service)
):
    """Performs behavioral comparison between baseline and candidate runs."""
    try:
        comp = service.compare_runs(
            plan_id=plan_id,
            baseline_run_id=req.baseline_run_id,
            candidate_run_id=req.candidate_run_id,
            baseline_results=req.baseline_results,
            candidate_results=req.candidate_results,
            contract_evaluations=req.contract_evaluations,
            evidence_ids=req.evidence_ids,
            session_id=req.session_id
        )
        return comp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
