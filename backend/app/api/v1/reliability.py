from fastapi import APIRouter, Depends, HTTPException, Query
from backend.app.api.deps import get_reliability_service, get_reliability_model
from backend.app.services.reliability_service import ReliabilityService
from backend.app.prediction.reliability_model import LogisticReliabilityModel
from backend.app.models.enums import PopulationType
from backend.app.models.reliability import (
    ReliabilitySummary,
    TargetReliability,
    TestCaseReliability,
    TrendAnalysis,
    FailurePattern,
    TestCasePrediction,
    QAPrioritizationItem,
    ModelEvaluationMetrics,
    DatasetAuditReport,
    DatasetProvenanceRecord,
    ContinuousScientificEvaluationReport,
    PredictionRecord,
    DatasetDiagnosticsReport,
    PopulationSeparationReport,
    WalkForwardEvaluationReport,
)
from backend.app.models.cross_app import (
    CrossApplicationEvaluationReport,
    EvaluationDatasetSnapshot,
    CrossApplicationEvaluationProtocol,
)


router = APIRouter()


@router.get("/summary", response_model=ReliabilitySummary)
def get_reliability_summary(
    service: ReliabilityService = Depends(get_reliability_service),
) -> ReliabilitySummary:
    """Returns global historical reliability analytics and high-level platform health metrics."""
    return service.get_summary()

@router.get("/targets", response_model=list[TargetReliability])
def list_targets_reliability(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[TargetReliability]:
    """Returns historical failure rates, trends, and grounded component attributions for all targets."""
    return service.list_targets_reliability()

@router.get("/targets/{target_id}", response_model=TargetReliability)
def get_target_reliability(
    target_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> TargetReliability:
    """Returns reliability analytics and grounded component attribution for a specific target."""
    return service.get_target_reliability(target_id)

@router.get("/test-cases", response_model=list[TestCaseReliability])
def list_test_cases_reliability(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[TestCaseReliability]:
    """Returns historical failure rates, trends, and risk predictions for all registered test cases."""
    return service.list_test_cases_reliability()

@router.get("/test-cases/{test_case_id}", response_model=TestCaseReliability)
def get_test_case_reliability(
    test_case_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> TestCaseReliability:
    """Returns historical metrics, last run status, and risk prediction for a specific test case."""
    return service.get_test_case_reliability(test_case_id)

@router.get("/trends", response_model=TrendAnalysis)
def get_reliability_trends(
    service: ReliabilityService = Depends(get_reliability_service),
) -> TrendAnalysis:
    """Returns chronological failure rate trends and bucketed historical progression."""
    return service.get_trends()

@router.get("/failure-patterns", response_model=list[FailurePattern])
def get_failure_patterns(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[FailurePattern]:
    """Returns distribution of failure categories correlated with grounded component attributions."""
    return service.get_failure_patterns()

@router.get("/predictions", response_model=list[TestCasePrediction])
def get_all_predictions(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[TestCasePrediction]:
    """Returns current model-estimated failure probabilities and feature explanations for all test cases."""
    return service.get_test_case_predictions()

@router.get("/predictions/{test_case_id}", response_model=TestCasePrediction)
def get_test_case_prediction(
    test_case_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> TestCasePrediction:
    """Returns predictive failure risk and feature contributions for a specific test case."""
    preds = service.get_test_case_predictions()
    for p in preds:
        if p.test_case_id == test_case_id:
            return p
    tc_rel = service.get_test_case_reliability(test_case_id)
    if tc_rel and tc_rel.prediction:
        return tc_rel.prediction
    raise HTTPException(status_code=404, detail=f"No prediction record found for test case {test_case_id}")

@router.get("/prioritization", response_model=list[QAPrioritizationItem])
def get_qa_prioritization(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[QAPrioritizationItem]:
    """Returns a risk-ranked test execution priority list for the next QA cycle."""
    return service.get_qa_prioritization()

@router.post("/train", response_model=ModelEvaluationMetrics)
def train_reliability_model(
    service: ReliabilityService = Depends(get_reliability_service),
) -> ModelEvaluationMetrics:
    """Trains the ML reliability model on historical chronological telemetry without data leakage."""
    return service.train_model()

@router.get("/model/status", response_model=ModelEvaluationMetrics)
def get_model_status(
    model: LogisticReliabilityModel = Depends(get_reliability_model),
) -> ModelEvaluationMetrics:
    """Returns the current trained model version, evaluation metrics, and calibration state."""
    return model.get_evaluation_metrics()

# ========================================================
# Slice 6.1 — Scientific Validation & Continuous Evaluation
# ========================================================

@router.get("/audit", response_model=DatasetAuditReport)
def get_dataset_audit(
    service: ReliabilityService = Depends(get_reliability_service),
) -> DatasetAuditReport:
    """Returns a formal audit of genuine historical QA executions, class balance, and dataset status."""
    return service.get_dataset_audit()

@router.get("/provenance", response_model=list[DatasetProvenanceRecord])
def get_dataset_provenance(
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[DatasetProvenanceRecord]:
    """Returns verifiable provenance records validating temporal sequencing (feature t -> target t+1)."""
    return service.get_provenance_records()

@router.get("/scientific-evaluation", response_model=ContinuousScientificEvaluationReport)
def get_scientific_evaluation(
    service: ReliabilityService = Depends(get_reliability_service),
) -> ContinuousScientificEvaluationReport:
    """Returns comprehensive scientific validation comparing model vs deterministic baselines A, B, C with calibration metrics."""
    return service.get_scientific_evaluation()

@router.get("/prediction-records", response_model=list[PredictionRecord])
def list_prediction_records(
    test_case_id: str | None = Query(None, description="Optional test case filter"),
    limit: int = Query(100, description="Max records to return"),
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[PredictionRecord]:
    """Returns continuous prediction tracking records (pending vs evaluated against actual next execution)."""
    return service.list_prediction_records(test_case_id=test_case_id, limit=limit)

@router.get("/dataset-diagnostics", response_model=DatasetDiagnosticsReport)
def get_dataset_diagnostics(
    service: ReliabilityService = Depends(get_reliability_service),
) -> DatasetDiagnosticsReport:
    """Returns Slice 6.3 dataset diagnostics, distribution shift analysis, and multi-model benchmark results."""
    return service.get_dataset_diagnostics()

# ========================================================
# Slice 6.4 — Population Separation & Walk-Forward Cross-Validation
# ========================================================

@router.get("/population-separation", response_model=PopulationSeparationReport)
def get_population_separation(
    min_train_size: int = Query(20, description="Minimum training window size for walk-forward folds"),
    step_size: int = Query(5, description="Test step size per fold"),
    service: ReliabilityService = Depends(get_reliability_service),
) -> PopulationSeparationReport:
    """Returns dataset separation across execution sources (Real Browser vs Mock vs Demo) with walk-forward validation."""
    return service.get_population_separation_report(
        min_train_size=min_train_size,
        step_size=step_size,
    )

@router.get("/walk-forward-evaluation", response_model=WalkForwardEvaluationReport)
def get_walk_forward_evaluation(
    population: PopulationType = Query(PopulationType.ALL_HISTORICAL, description="Execution population subset"),
    min_train_size: int = Query(20, description="Minimum training window size"),
    step_size: int = Query(5, description="Test step size per fold"),
    service: ReliabilityService = Depends(get_reliability_service),
) -> WalkForwardEvaluationReport:
    """Conducts expanding-window walk-forward validation for a specific population."""
    return service.get_walk_forward_evaluation(
        population=population,
        min_train_size=min_train_size,
        step_size=step_size,
    )


# ========================================================
# Slice 6.9 — Cross-Application Reliability Evaluation
# ========================================================

@router.get("/cross-application-evaluation", response_model=CrossApplicationEvaluationReport)
def get_cross_application_evaluation(
    service: ReliabilityService = Depends(get_reliability_service),
) -> CrossApplicationEvaluationReport:
    """
    Executes Slice 6.9 Cross-Application Reliability Evaluation & Generalization across
    Within-Application Baselines (Regime A), Leave-One-Application-Out (Regime B), and Combined Temporal (Regime C).
    """
    return service.get_cross_application_evaluation_report()

@router.get("/cross-application/protocol", response_model=CrossApplicationEvaluationProtocol)
def get_cross_application_protocol() -> CrossApplicationEvaluationProtocol:
    """Returns the frozen CrossApplicationEvaluationProtocol v1.0 specification."""
    from datetime import datetime, timezone
    return CrossApplicationEvaluationProtocol(
        created_at=datetime.now(timezone.utc).isoformat(),
    )




