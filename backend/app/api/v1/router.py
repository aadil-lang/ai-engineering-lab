from fastapi import APIRouter
from backend.app.api.v1 import (
    runs,
    targets,
    test_cases,
    assessments,
    diagnoses,
    remediations,
    reliability,
    campaigns,
    cold_start,
    uncertainty,
    tools,
    lifecycle,
    github,
    prompt_lab,
    governance,
    live_testing,
    memory,
    change_impact,
    provenance,
    system,
)

api_router = APIRouter()

api_router.include_router(system.router, prefix="/system", tags=["System Diagnostics, Readiness & Demonstration"])
api_router.include_router(provenance.router, prefix="/provenance", tags=["Unified Engineering Provenance & Change Trace"])
api_router.include_router(change_impact.router, tags=["Change-Aware Impact Analysis & Adaptive Regression"])
api_router.include_router(memory.router, prefix="/memory", tags=["Application-Aware Engineering Memory"])
api_router.include_router(live_testing.router, prefix="/live", tags=["Live Autonomous Testing Console"])
api_router.include_router(runs.router, prefix="/runs", tags=["Test Runs"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["QA Campaigns"])
api_router.include_router(diagnoses.router, prefix="/diagnoses", tags=["Failure Diagnoses"])
api_router.include_router(remediations.router, tags=["Remediation & Fix Verification"])
api_router.include_router(cold_start.router, prefix="/reliability/cold-start", tags=["Cold-Start Calibration"])
api_router.include_router(uncertainty.router, prefix="/reliability/uncertainty", tags=["Uncertainty & Decision Utility"])
api_router.include_router(tools.router, prefix="/tools", tags=["Reliability Control Plane & Agent Tools"])
api_router.include_router(lifecycle.router, prefix="/lifecycle", tags=["Git & Engineering Lifecycle"])
api_router.include_router(github.router, prefix="/github", tags=["Real GitHub & Actions CI Lifecycle"])
api_router.include_router(prompt_lab.router, tags=["Prompt Reliability Lab"])
api_router.include_router(governance.router, tags=["Human Governance"])
api_router.include_router(reliability.router, prefix="/reliability", tags=["Historical Reliability & Predictive QA"])
api_router.include_router(targets.router, prefix="/targets", tags=["Application Targets"])
api_router.include_router(test_cases.router, prefix="/test-cases", tags=["Test Cases"])
api_router.include_router(assessments.router, prefix="/assessments", tags=["Production Readiness Assessments"])



