"""
Slice 8M — System Diagnostics, Readiness & Demonstration REST API Router

Endpoints:
- GET /api/v1/system/doctor: Detailed list of environment diagnostic checks
- GET /api/v1/system/readiness: Platform readiness contract & capability status
- GET /api/v1/system/manifest: Authoritative Engineering Lab v1 Release Manifest
- POST /api/v1/system/demonstration/run: Executes canonical end-to-end lifecycle demonstration
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from backend.app.system.models import (
    DiagnosticCheck,
    EngineeringLabReadiness,
    EngineeringLabReleaseManifest,
    DemonstrationScenarioResult,
)
from backend.app.system.doctor import EnvironmentDoctor
from backend.app.system.manifest import generate_release_manifest
from backend.app.system.demonstration import CanonicalDemonstrationRunner

router = APIRouter()

# Default instances
_doctor = EnvironmentDoctor()
_demo_runner = CanonicalDemonstrationRunner()


def get_doctor() -> EnvironmentDoctor:
    return _doctor


def get_demo_runner() -> CanonicalDemonstrationRunner:
    return _demo_runner


class RunDemonstrationRequest(BaseModel):
    correlation_id: Optional[str] = None
    governor_actor_id: str = "lead_qa_engineer_alice"
    target_id: str = "real_question_generator_local"


@router.get("/doctor", response_model=List[DiagnosticCheck])
def get_environment_diagnostics(doctor: EnvironmentDoctor = Depends(get_doctor)):
    """Runs deterministic environment diagnostics and returns individual check results."""
    return doctor.run_all_checks()


@router.get("/readiness", response_model=EngineeringLabReadiness)
def get_system_readiness(doctor: EnvironmentDoctor = Depends(get_doctor)):
    """Evaluates and returns the Engineering Lab v1 readiness contract."""
    return doctor.evaluate_readiness()


@router.get("/manifest", response_model=EngineeringLabReleaseManifest)
def get_release_manifest(doctor: EnvironmentDoctor = Depends(get_doctor)):
    """Generates and returns the machine-readable Release Manifest."""
    return generate_release_manifest(doctor)


@router.post("/demonstration/run", response_model=DemonstrationScenarioResult)
def run_canonical_demonstration(
    req: RunDemonstrationRequest = Body(default_factory=RunDemonstrationRequest),
    runner: CanonicalDemonstrationRunner = Depends(get_demo_runner),
):
    """Executes the complete canonical end-to-end demonstration on the Question Generator target."""
    try:
        return runner.run_demonstration(
            correlation_id=req.correlation_id,
            governor_actor_id=req.governor_actor_id,
            target_id=req.target_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demonstration run failed: {str(e)}")
