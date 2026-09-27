from fastapi import APIRouter, Depends, Query, status
from backend.app.api.deps import get_remediation_service
from backend.app.services.remediation_service import RemediationService
from backend.app.models.remediation import RemediationTask, RemediationTaskCreate

router = APIRouter(prefix="/remediations", tags=["Remediation & Fix Verification"])

@router.post("", response_model=RemediationTask, status_code=status.HTTP_201_CREATED)
async def create_remediation(
    payload: RemediationTaskCreate,
    service: RemediationService = Depends(get_remediation_service),
) -> RemediationTask:
    """
    Generate an autonomous engineering remediation for a failed test run.
    Invokes the CodingAgent to reason over the diagnosis and propose code changes.
    """
    return await service.create_remediation_task(
        run_id=payload.run_id,
        diagnosis_id=payload.diagnosis_id,
        target_repository=payload.target_repository,
        target_branch=payload.target_branch,
        auto_apply=payload.auto_apply,
    )

@router.post("/{task_id}/apply-verify", response_model=RemediationTask)
async def apply_and_verify_remediation(
    task_id: str,
    service: RemediationService = Depends(get_remediation_service),
) -> RemediationTask:
    """
    Applies the proposed code changes to the workspace, executes build/static validation,
    and runs regression tests to independently verify the fix.
    """
    return await service.apply_and_verify(task_id)

@router.get("/{task_id}", response_model=RemediationTask)
def get_remediation_detail(
    task_id: str,
    service: RemediationService = Depends(get_remediation_service),
) -> RemediationTask:
    """Get remediation task details, code diffs, attempts, and verification results."""
    return service.get_task(task_id)

@router.get("", response_model=list[RemediationTask])
def list_remediations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: RemediationService = Depends(get_remediation_service),
) -> list[RemediationTask]:
    """List all remediation tasks."""
    return service.list_tasks(limit=limit, offset=offset)
