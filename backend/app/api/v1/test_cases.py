from fastapi import APIRouter, Depends, HTTPException, Query, status
from backend.app.models.test_case import TestCase, TestCaseCreate
from backend.app.models.enums import TestMode
from backend.app.services.test_case_service import TestCaseService
from backend.app.api.deps import get_test_case_service
from backend.app.core.exceptions import NotFoundException

router = APIRouter()

@router.get("", response_model=list[TestCase])
def list_test_cases(
    target_id: str | None = Query(None),
    test_mode: TestMode | None = Query(None),
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> list[TestCase]:
    """List available test cases across 5 testing modes."""
    mode_str = test_mode.value if test_mode else None
    return test_case_service.list_test_cases(target_id=target_id, test_mode=mode_str)

@router.post("", response_model=TestCase, status_code=status.HTTP_201_CREATED)
def create_test_case(
    payload: TestCaseCreate,
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCase:
    """Register a new test case scenario."""
    return test_case_service.create_test_case(payload)

@router.get("/{test_case_id}", response_model=TestCase)
def get_test_case(
    test_case_id: str,
    test_case_service: TestCaseService = Depends(get_test_case_service),
) -> TestCase:
    """Get single test case details."""
    try:
        return test_case_service.get_test_case(test_case_id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
