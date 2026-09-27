from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    EvaluationSuite,
    EvaluationSuiteVersion,
    EvaluationCase,
    EvaluationRun,
    PromptDiagnosis,
    PromptImprovementCandidate,
    PromptComparisonResult,
    EvaluationSnapshot,
    StructuredPromptComponents,
)
from backend.app.prompt_lab.repository import PromptLabRepository
from backend.app.prompt_lab.prompt_service import PromptService
from backend.app.prompt_lab.evaluation_service import EvaluationService
from backend.app.prompt_lab.diagnosis_service import PromptDiagnosisService
from backend.app.prompt_lab.errors import (
    PromptNotFoundError,
    PromptVersionNotFoundError,
    PromptVersionImmutableError,
    EvaluationSuiteNotFoundError,
    EvaluationRunNotFoundError,
    EvaluationSnapshotTamperedError,
)

router = APIRouter(prefix="/prompt-lab", tags=["prompt-lab"])

# Repositories & Services singleton / lazy instances
_repo = PromptLabRepository()
_prompt_service = PromptService(_repo)
_diagnosis_service = PromptDiagnosisService()
_eval_service = EvaluationService(_repo, _prompt_service, _diagnosis_service)


# Request schemas
class CreatePromptRequest(BaseModel):
    prompt_id: str
    name: str
    description: str = ""


class CreatePromptVersionPayload(BaseModel):
    template: str
    variables_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    components: Optional[StructuredPromptComponents] = None
    change_reason: Optional[str] = None
    parent_version: Optional[int] = None
    status: PromptStatus = PromptStatus.DRAFT


class CreateSuiteRequest(BaseModel):
    suite_id: str
    name: str
    description: str = ""


class CreateSuiteVersionPayload(BaseModel):
    cases: List[EvaluationCase]
    description: str = ""
    is_frozen: bool = False


class RunEvaluationPayload(BaseModel):
    prompt_id: str
    prompt_version: int
    suite_id: str
    suite_version: int
    model: str = "mock-agent-v1"
    generation_parameters: Optional[Dict[str, Any]] = None


# 1. Prompts & Versions
@router.get("/prompts", response_model=List[PromptDefinition])
def list_prompts():
    return _prompt_service.list_prompts()


@router.post("/prompts", response_model=PromptDefinition, status_code=status.HTTP_201_CREATED)
def create_prompt(payload: CreatePromptRequest):
    return _prompt_service.create_prompt(payload.prompt_id, payload.name, payload.description)


@router.get("/prompts/{prompt_id}")
def get_prompt(prompt_id: str):
    try:
        p = _prompt_service.get_prompt(prompt_id)
        versions = _prompt_service.list_prompt_versions(prompt_id)
        return {"prompt": p, "versions": versions}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/prompts/{prompt_id}/versions", response_model=PromptVersion, status_code=status.HTTP_201_CREATED)
def create_prompt_version(prompt_id: str, payload: CreatePromptVersionPayload):
    try:
        return _prompt_service.create_prompt_version(
            prompt_id=prompt_id,
            template=payload.template,
            variables_schema=payload.variables_schema,
            output_schema=payload.output_schema,
            components=payload.components,
            change_reason=payload.change_reason,
            parent_version=payload.parent_version,
            status=payload.status,
        )
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/prompts/{prompt_id}/versions/{version}", response_model=PromptVersion)
def get_prompt_version(prompt_id: str, version: int):
    try:
        return _prompt_service.get_prompt_version(prompt_id, version)
    except (PromptNotFoundError, PromptVersionNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


# 2. Evaluation Suites
@router.get("/evaluation-suites", response_model=List[EvaluationSuite])
def list_suites():
    return _eval_service.list_suites()


@router.post("/evaluation-suites", response_model=EvaluationSuite, status_code=status.HTTP_201_CREATED)
def create_suite(payload: CreateSuiteRequest):
    return _eval_service.create_suite(payload.suite_id, payload.name, payload.description)


@router.get("/evaluation-suites/{suite_id}")
def get_suite(suite_id: str, version: Optional[int] = None):
    try:
        s = _eval_service.get_suite(suite_id)
        sv = None
        if version:
            sv = _eval_service.get_suite_version(suite_id, version)
        return {"suite": s, "version": sv}
    except EvaluationSuiteNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluation-suites/{suite_id}/versions", response_model=EvaluationSuiteVersion, status_code=status.HTTP_201_CREATED)
def create_suite_version(suite_id: str, payload: CreateSuiteVersionPayload):
    try:
        return _eval_service.create_suite_version(
            suite_id=suite_id,
            cases=payload.cases,
            description=payload.description,
            is_frozen=payload.is_frozen,
        )
    except EvaluationSuiteNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 3. Evaluation Execution & Runs
@router.post("/evaluations/run", response_model=EvaluationRun)
def run_evaluation(payload: RunEvaluationPayload):
    try:
        return _eval_service.execute_evaluation(
            prompt_id=payload.prompt_id,
            prompt_version=payload.prompt_version,
            suite_id=payload.suite_id,
            suite_version=payload.suite_version,
            model=payload.model,
            generation_parameters=payload.generation_parameters,
        )
    except (PromptNotFoundError, PromptVersionNotFoundError, EvaluationSuiteNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/evaluations/{run_id}")
def get_evaluation(run_id: str):
    run = _repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    diags = _repo.list_diagnoses_for_run(run_id)
    return {"run": run, "diagnoses": diags}


@router.get("/evaluations/compare/versions", response_model=PromptComparisonResult)
def compare_versions(
    prompt_id: str = Query(...),
    v1: int = Query(...),
    v2: int = Query(...),
    suite_id: str = Query(...),
    suite_version: int = Query(...),
):
    try:
        return _eval_service.compare_prompt_versions(
            prompt_id=prompt_id,
            v1_version=v1,
            v2_version=v2,
            suite_id=suite_id,
            suite_version=suite_version,
        )
    except EvaluationRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# 4. Snapshots & Verification
@router.get("/snapshots/{snapshot_id}", response_model=EvaluationSnapshot)
def get_snapshot(snapshot_id: str):
    try:
        snap = _repo.get_snapshot(snapshot_id)
        if not snap:
            raise HTTPException(status_code=404, detail=f"Snapshot '{snapshot_id}' not found.")
        return snap
    except EvaluationSnapshotTamperedError as e:
        raise HTTPException(status_code=409, detail=f"Snapshot integrity violation: {str(e)}")
