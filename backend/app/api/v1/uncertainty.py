import os
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_reliability_service
from backend.app.services.reliability_service import ReliabilityService
from backend.app.prediction.uncertainty_evaluator import UncertaintyEvaluator
from backend.app.models.uncertainty import (
    UncertaintyExperiment,
    PredictionUncertainty,
    RiskCoveragePoint,
    DecisionPolicy,
    UncertaintyBucketSummary,
    SelectivePredictionResult,
)

router = APIRouter()

EXPERIMENTS_DIR = os.path.join("backend", "data", "experiments")
LATEST_UNCERTAINTY_FILE = os.path.join(EXPERIMENTS_DIR, "latest_uncertainty_experiment.json")


def _get_or_run_latest_uncertainty_experiment() -> UncertaintyExperiment:
    """Retrieves the latest persisted uncertainty experiment or runs an evaluation."""
    os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
    if os.path.exists(LATEST_UNCERTAINTY_FILE):
        try:
            with open(LATEST_UNCERTAINTY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return UncertaintyExperiment(**data)
        except Exception:
            pass

    exp = UncertaintyEvaluator.run_full_evaluation()

    try:
        with open(LATEST_UNCERTAINTY_FILE, "w", encoding="utf-8") as f:
            f.write(exp.model_dump_json(indent=2))
        specific_file = os.path.join(EXPERIMENTS_DIR, f"{exp.experiment_id}.json")
        with open(specific_file, "w", encoding="utf-8") as f:
            f.write(exp.model_dump_json(indent=2))
    except Exception:
        pass

    return exp


@router.get("", response_model=UncertaintyExperiment)
def get_latest_uncertainty_experiment() -> UncertaintyExperiment:
    """Returns the complete Slice 7.1 uncertainty-aware evaluation experiment."""
    return _get_or_run_latest_uncertainty_experiment()


@router.get("/summary", response_model=dict[str, Any])
def get_uncertainty_summary() -> dict[str, Any]:
    """Returns a high-level summary of the uncertainty experiment and hypothesis verdicts."""
    exp = _get_or_run_latest_uncertainty_experiment()
    return {
        "experiment_id": exp.experiment_id,
        "protocol_version": exp.protocol_version,
        "snapshot_id": exp.snapshot_id,
        "parent_snapshot_id": exp.parent_snapshot_id,
        "model_version": exp.model_version,
        "uncertainty_method_version": exp.uncertainty_method_version,
        "decision_policy_version": exp.decision_policy_version,
        "total_eval_predictions": exp.total_eval_predictions,
        "applications_evaluated": exp.test_applications,
        "budget_k_values": exp.budget_k_values,
        "hypotheses_verdicts": [v.model_dump() for v in exp.hypotheses_verdicts],
        "scientific_summary": exp.scientific_summary,
    }


@router.get("/{experiment_id}", response_model=UncertaintyExperiment)
def get_uncertainty_experiment_by_id(experiment_id: str) -> UncertaintyExperiment:
    """Retrieves a specific uncertainty experiment artifact by its ID."""
    file_path = os.path.join(EXPERIMENTS_DIR, f"{experiment_id}.json")
    if not os.path.exists(file_path):
        latest = _get_or_run_latest_uncertainty_experiment()
        if latest.experiment_id == experiment_id:
            return latest
        raise HTTPException(status_code=404, detail=f"Uncertainty experiment {experiment_id} not found")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UncertaintyExperiment(**data)


@router.get("/{experiment_id}/predictions", response_model=list[PredictionUncertainty])
def get_experiment_predictions(
    experiment_id: str,
    application_id: str | None = Query(None, description="Filter by target application ID"),
    budget_k: int | None = Query(None, description="Filter by local budget K"),
) -> list[PredictionUncertainty]:
    """Retrieves individual uncertainty-annotated predictions with optional filtering."""
    exp = get_uncertainty_experiment_by_id(experiment_id)
    preds = exp.predictions

    if application_id:
        preds = [p for p in preds if p.application_id == application_id]
    if budget_k is not None:
        preds = [p for p in preds if p.budget_k == budget_k]

    return preds


@router.get("/{experiment_id}/risk-coverage", response_model=list[RiskCoveragePoint])
def get_risk_coverage_curve(experiment_id: str) -> list[RiskCoveragePoint]:
    """Retrieves the Risk-Coverage trade-off curve points."""
    exp = get_uncertainty_experiment_by_id(experiment_id)
    return exp.risk_coverage_curve


@router.get("/{experiment_id}/calibration", response_model=list[UncertaintyBucketSummary])
def get_uncertainty_calibration_buckets(experiment_id: str) -> list[UncertaintyBucketSummary]:
    """Retrieves the uncertainty-stratified calibration buckets (LOW, MEDIUM, HIGH)."""
    exp = get_uncertainty_experiment_by_id(experiment_id)
    return exp.uncertainty_buckets


@router.get("/{experiment_id}/decision-policy", response_model=list[SelectivePredictionResult])
def get_decision_policy_results(experiment_id: str) -> list[SelectivePredictionResult]:
    """Retrieves the selective prediction results under frozen decision policies."""
    exp = get_uncertainty_experiment_by_id(experiment_id)
    return exp.selective_results
