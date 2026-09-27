from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.target import ApplicationTarget, ApplicationTargetCreate
from backend.app.services.target_service import TargetService
from backend.app.api.deps import get_target_service
from backend.app.core.exceptions import NotFoundException

router = APIRouter()

@router.get("", response_model=list[ApplicationTarget])
def list_targets(
    target_service: TargetService = Depends(get_target_service),
) -> list[ApplicationTarget]:
    """List all registered application targets."""
    return target_service.list_targets()

@router.post("", response_model=ApplicationTarget, status_code=status.HTTP_201_CREATED)
def register_target(
    payload: ApplicationTargetCreate,
    target_service: TargetService = Depends(get_target_service),
) -> ApplicationTarget:
    """Register a new application target."""
    return target_service.register_target(payload)

@router.get("/{target_id}", response_model=ApplicationTarget)
def get_target(
    target_id: str,
    target_service: TargetService = Depends(get_target_service),
) -> ApplicationTarget:
    """Get single target application details."""
    try:
        return target_service.get_target(target_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
