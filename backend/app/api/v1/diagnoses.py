from fastapi import APIRouter, Depends, Query, HTTPException
from backend.app.models.diagnosis import EngineeringDiagnosis
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.api.deps import get_diagnosis_service
from backend.app.core.exceptions import NotFoundException

router = APIRouter()

@router.get("", response_model=list[EngineeringDiagnosis])
def list_diagnoses(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
) -> list[EngineeringDiagnosis]:
    """List all recent engineering diagnoses across test runs."""
    return diagnosis_service.list_diagnoses(limit=limit, offset=offset)

@router.get("/{diagnosis_id}", response_model=EngineeringDiagnosis)
def get_diagnosis(
    diagnosis_id: str,
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
) -> EngineeringDiagnosis:
    """Get single diagnosis by ID."""
    diag = diagnosis_service.diagnosis_repo.get_diagnosis(diagnosis_id)
    if not diag:
        raise HTTPException(status_code=404, detail=f"Diagnosis '{diagnosis_id}' not found")
    return diag
