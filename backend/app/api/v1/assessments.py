from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.models.assessment import Assessment, DimensionScore
from backend.app.models.enums import AssessmentDimension
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.api.deps import get_repository

router = APIRouter()

@router.get("", response_model=list[Assessment])
def list_assessments(
    application_id: str | None = Query(None),
    repo: SQLiteRepository = Depends(get_repository),
) -> list[Assessment]:
    """
    List production readiness assessments.
    Returns 9-dimension readiness audits (Reliability, Performance, Load, Security, etc.).
    """
    assessments = repo.list_assessments(application_id=application_id)
    if not assessments:
        # Provide sample baseline readiness assessment for demo target
        sample_assessment = Assessment(
            assessment_id="asm_baseline_demo",
            application_id=application_id or "tgt_demo_shop",
            overall_score=88.4,
            status="COMPLETED",
            dimensions=[
                DimensionScore(dimension=AssessmentDimension.RELIABILITY, score=92.0, status="PASS", summary="99.9% uptime SLA compliance across synthetic probes", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.PERFORMANCE, score=85.5, status="PASS", summary="p95 TTFB is 142ms; LCP is 1.1s", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.LOAD_CAPACITY, score=78.0, status="WARN", summary="k6 load test showed minor queue latency spike at 500 VUs", findings_count=1),
                DimensionScore(dimension=AssessmentDimension.FAILURE_RECOVERY, score=94.0, status="PASS", summary="Graceful circuit breaker trip and recovery within 800ms", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.SECURITY, score=89.0, status="PASS", summary="OWASP ZAP baseline passed with 0 high/critical vulnerabilities", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.RESOURCE_BEHAVIOR, score=86.0, status="PASS", summary="Memory heap stable across 10,000 synthetic requests", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.OBSERVABILITY, score=96.0, status="PASS", summary="Full OpenTelemetry W3C trace-context propagation active", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.AI_RELIABILITY, score=84.0, status="PASS", summary="Shopping copilot hallucination rate < 1.5%", findings_count=0),
                DimensionScore(dimension=AssessmentDimension.MAINTAINABILITY, score=91.0, status="PASS", summary="Modular architecture with typed contracts & isolated submodules", findings_count=0),
            ],
            findings_ids=[],
            recommendations=[
                "Scale up Redis connection pool or increase pod limits to resolve 500 VU latency spike.",
                "Add automated weekly OWASP ZAP fuzzing pass in CI pipeline.",
            ],
        )
        repo.save_assessment(sample_assessment)
        return [sample_assessment]
    return assessments
