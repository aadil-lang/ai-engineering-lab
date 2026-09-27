from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.metric import Metric
from backend.app.models.enums import TestMode, RunStatus
from backend.app.services.run_manager import RunManager
from backend.app.api.deps import get_run_manager
from backend.app.core.exceptions import NotFoundException

router = APIRouter()

@router.post("", response_model=TestRun, status_code=status.HTTP_201_CREATED)
async def create_and_execute_run(
    payload: TestRunCreate,
    run_manager: RunManager = Depends(get_run_manager),
) -> TestRun:
    """Trigger a new autonomous test run."""
    try:
        return await run_manager.initiate_run(payload)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute run: {str(e)}")

@router.get("", response_model=dict)
def list_runs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    application_id: str | None = Query(None),
    test_mode: TestMode | None = Query(None),
    status_filter: RunStatus | None = Query(None, alias="status"),
    run_manager: RunManager = Depends(get_run_manager),
):
    """List test runs with filtering and pagination."""
    mode_str = test_mode.value if test_mode else None
    status_str = status_filter.value if status_filter else None
    
    runs = run_manager.list_runs(
        limit=limit,
        offset=offset,
        application_id=application_id,
        test_mode=mode_str,
        status=status_str,
    )
    total = run_manager.count_runs(
        application_id=application_id,
        test_mode=mode_str,
        status=status_str,
    )
    return {
        "items": runs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.get("/{run_id}", response_model=TestRun)
def get_run(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> TestRun:
    """Get single test run details."""
    try:
        return run_manager.get_run(run_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/evidence", response_model=list[Evidence])
def get_run_evidence(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> list[Evidence]:
    """Retrieve all structured evidence items collected for a run."""
    try:
        return run_manager.get_run_evidence(run_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/evidence/{evidence_id}", response_model=Evidence)
def get_evidence_detail(
    run_id: str,
    evidence_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> Evidence:
    """Retrieve raw payload for a specific evidence item."""
    try:
        return run_manager.get_evidence_detail(evidence_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/evidence/{evidence_id}/artifact")
def get_evidence_artifact(
    run_id: str,
    evidence_id: str,
    run_manager: RunManager = Depends(get_run_manager),
):
    """Serve the raw stored disk artifact (screenshot PNG, DOM HTML, Network JSON, etc.)."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    evidence = run_manager.get_evidence_detail(evidence_id)
    if not evidence.artifact_path:
        raise HTTPException(status_code=404, detail="No disk artifact associated with this evidence record")
    
    path = Path(evidence.artifact_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found on disk")
    
    return FileResponse(
        path=str(path),
        media_type=evidence.mime_type or "application/octet-stream",
        filename=path.name,
    )

@router.get("/{run_id}/failures", response_model=list[Failure])
def get_run_failures(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> list[Failure]:
    """Retrieve all failure records for a run."""
    try:
        return run_manager.get_run_failures(run_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}/metrics", response_model=list[Metric])
def get_run_metrics(
    run_id: str,
    run_manager: RunManager = Depends(get_run_manager),
) -> list[Metric]:
    """Retrieve all metrics recorded for a run."""
    try:
        return run_manager.get_run_metrics(run_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

from backend.app.models.diagnosis import EngineeringDiagnosis
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.api.deps import get_diagnosis_service

@router.post("/{run_id}/diagnose", response_model=EngineeringDiagnosis)
def trigger_run_diagnosis(
    run_id: str,
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
) -> EngineeringDiagnosis:
    """Trigger or re-execute AI evidence-based failure diagnosis for a run."""
    try:
        return diagnosis_service.diagnose_run(run_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to diagnose run: {str(e)}")

@router.get("/{run_id}/diagnosis", response_model=EngineeringDiagnosis | None)
def get_run_diagnosis(
    run_id: str,
    auto_diagnose: bool = Query(True, description="Automatically generate diagnosis if run failed and not yet diagnosed"),
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
) -> EngineeringDiagnosis | None:
    """Get the engineering failure diagnosis for a test run."""
    try:
        return diagnosis_service.get_run_diagnosis(run_id, auto_diagnose_if_failed=auto_diagnose)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch diagnosis: {str(e)}")

from backend.app.api.deps import get_remediation_service
from backend.app.services.remediation_service import RemediationService
from backend.app.models.remediation import RemediationTask

@router.post("/{run_id}/remediate", response_model=RemediationTask)
async def trigger_run_remediation(
    run_id: str,
    auto_apply: bool = Query(False, description="Automatically apply patch and run regression verification"),
    target_repository: str = Query("local_workspace"),
    target_branch: str = Query("main"),
    remediation_service: RemediationService = Depends(get_remediation_service),
) -> RemediationTask:
    """Trigger autonomous engineering remediation for a failed test run."""
    try:
        return await remediation_service.create_remediation_task(
            run_id=run_id,
            auto_apply=auto_apply,
            target_repository=target_repository,
            target_branch=target_branch,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remediate run: {str(e)}")

@router.get("/{run_id}/remediations", response_model=list[RemediationTask])
def get_run_remediations(
    run_id: str,
    remediation_service: RemediationService = Depends(get_remediation_service),
) -> list[RemediationTask]:
    """Get all remediation tasks associated with a test run."""
    return remediation_service.get_tasks_by_run(run_id)


