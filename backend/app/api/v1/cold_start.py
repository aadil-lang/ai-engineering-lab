import os
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.deps import get_reliability_service
from backend.app.services.reliability_service import ReliabilityService
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.cold_start_evaluator import ColdStartEvaluator
from backend.app.models.cold_start import (
    ColdStartExperiment,
    ColdStartPrediction,
    ColdStartFailureAnalysis,
    FeatureAblationExperimentResult,
    ColdStartEvaluationResult,
)

router = APIRouter()

EXPERIMENTS_DIR = os.path.join("backend", "data", "experiments")
LATEST_EXP_FILE = os.path.join(EXPERIMENTS_DIR, "latest_cold_start_experiment.json")


def _get_or_run_latest_experiment(service: ReliabilityService) -> ColdStartExperiment:
    """Retrieves the latest persisted cold-start experiment or runs a new evaluation."""
    os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
    if os.path.exists(LATEST_EXP_FILE):
        try:
            with open(LATEST_EXP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ColdStartExperiment(**data)
        except Exception:
            pass

    records = service._collect_all_records()
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    exp = ColdStartEvaluator.run_full_cold_start_evaluation(records, vectors)

    try:
        with open(LATEST_EXP_FILE, "w", encoding="utf-8") as f:
            f.write(exp.model_dump_json(indent=2))
        specific_file = os.path.join(EXPERIMENTS_DIR, f"{exp.experiment_id}.json")
        with open(specific_file, "w", encoding="utf-8") as f:
            f.write(exp.model_dump_json(indent=2))
    except Exception:
        pass

    return exp


@router.get("", response_model=ColdStartExperiment)
def get_latest_cold_start_experiment(
    service: ReliabilityService = Depends(get_reliability_service),
) -> ColdStartExperiment:
    """Returns the complete Slice 7.0 cold-start calibration experiment."""
    return _get_or_run_latest_experiment(service)


@router.get("/summary", response_model=dict[str, Any])
def get_cold_start_summary(
    service: ReliabilityService = Depends(get_reliability_service),
) -> dict[str, Any]:
    """Returns high-level summary and hypothesis verdicts for cold-start calibration."""
    exp = _get_or_run_latest_experiment(service)
    return {
        "experiment_id": exp.experiment_id,
        "protocol_version": exp.protocol_version,
        "created_at": exp.created_at,
        "snapshot_id": exp.snapshot_id,
        "applications": exp.applications_evaluated,
        "budgets_k": exp.budget_k_values,
        "hypotheses_verdicts": exp.hypotheses_verdicts,
        "scientific_summary": exp.scientific_summary,
    }


@router.get("/{experiment_id}", response_model=ColdStartExperiment)
def get_cold_start_experiment_by_id(
    experiment_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> ColdStartExperiment:
    """Returns a specific cold-start experiment by ID."""
    target_file = os.path.join(EXPERIMENTS_DIR, f"{experiment_id}.json")
    if os.path.exists(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ColdStartExperiment(**data)

    latest = _get_or_run_latest_experiment(service)
    if latest.experiment_id == experiment_id:
        return latest

    raise HTTPException(status_code=404, detail=f"Cold-start experiment '{experiment_id}' not found")


@router.get("/{experiment_id}/predictions", response_model=list[ColdStartPrediction])
def get_cold_start_predictions(
    experiment_id: str,
    application_id: str | None = Query(None, description="Optional application filter"),
    budget_k: int | None = Query(None, description="Optional budget K filter"),
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[ColdStartPrediction]:
    """Returns individual prediction records with complete provenance and audit details."""
    exp = get_cold_start_experiment_by_id(experiment_id, service)
    records = []
    # If the experiment has predictions stored in the specific JSON
    target_file = os.path.join(EXPERIMENTS_DIR, f"{experiment_id}.json")
    if os.path.exists(target_file):
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Re-evaluate or fetch from evaluator if needed
    # Generate predictions for the experiment if needed
    run_records = service._collect_all_records()
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(run_records)
    _, all_preds = ColdStartEvaluator.evaluate_cold_start_experiment(vectors, exp.budget_k_values)

    filtered = all_preds
    if application_id:
        filtered = [p for p in filtered if p.held_out_application_id == application_id]
    if budget_k is not None:
        filtered = [p for p in filtered if p.budget_k == budget_k]
    return filtered


@router.get("/{experiment_id}/failures", response_model=list[ColdStartFailureAnalysis])
def get_cold_start_failures(
    experiment_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[ColdStartFailureAnalysis]:
    """Returns failure-case analysis for naturally occurring failures."""
    exp = get_cold_start_experiment_by_id(experiment_id, service)
    return exp.failure_analyses


@router.get("/{experiment_id}/feature-ablation", response_model=list[FeatureAblationExperimentResult])
def get_cold_start_feature_ablation(
    experiment_id: str,
    service: ReliabilityService = Depends(get_reliability_service),
) -> list[FeatureAblationExperimentResult]:
    """Returns secondary feature ablation results (Model A vs Model B vs Model C)."""
    exp = get_cold_start_experiment_by_id(experiment_id, service)
    return exp.feature_ablation_results
