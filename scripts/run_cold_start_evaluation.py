#!/usr/bin/env python
"""
Slice 7.0 CLI Runner: Cross-Application Reliability Prior & Cold-Start Calibration.

Executes the cold-start calibration experiment against the live database, evaluating:
- Strategy A: Global Prior (frozen Slice 6.9 model)
- Strategy B: Local Baseline (local history only)
- Strategy C: Global + Local Calibration (Empirical Bayes log-odds intercept calibration)
across K in {0, 1, 3, 5, 10} and walk-forward online calibration.
"""

import sys
import os
import json
from datetime import datetime, timezone

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.prediction.reliability_model import LogisticReliabilityModel
from backend.app.services.reliability_service import ReliabilityService
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.cold_start_evaluator import ColdStartEvaluator


def main():
    print("=" * 80)
    print("SLICE 7.0 — CROSS-APPLICATION RELIABILITY PRIOR & COLD-START CALIBRATION")
    print("=" * 80)

    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        sys.exit(1)

    repo = SQLiteRepository(db_path=db_path)
    model = LogisticReliabilityModel()
    service = ReliabilityService(repo, repo, repo, repo, repo, repo, repo, repo, model)

    print("\n[1/6] Extracting longitudinal telemetry records and temporal transitions...")
    records = service._collect_all_records()
    vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
    print(f"      Total historical records: {len(records)}")
    print(f"      Total temporal transitions: {len([v for v in vectors if v.label_next_failed is not None])}")

    print("\n[2/6] Executing ColdStartEvaluator across held-out applications & budgets K...")
    exp = ColdStartEvaluator.run_full_cold_start_evaluation(records, vectors)

    print("\n" + "=" * 80)
    print("EXPERIMENT OVERVIEW & PROVENANCE")
    print("=" * 80)
    print(f"Experiment ID:          {exp.experiment_id}")
    print(f"Created At:             {exp.created_at}")
    print(f"Parent Snapshot:        {exp.parent_snapshot_id} (Slice 6.9 Frozen)")
    print(f"Snapshot ID:            {exp.snapshot_id}")
    print(f"Protocol:               {exp.protocol_version}")
    print(f"Model Version:          {exp.model_version}")
    print(f"Calibration Method:     {exp.calibration_method}")
    print(f"Evaluated Applications: {', '.join(exp.applications_evaluated)}")
    print(f"Budget K Values:        {exp.budget_k_values}")

    print("\n" + "=" * 80)
    print("COLD-START CALIBRATION CURVES & MODEL STRATEGY COMPARISON")
    print("=" * 80)
    header = f"{'Held-Out App':16} | {'K':2} | {'N_eval':6} | {'Fails':5} | {'Strat A Brier':13} | {'Strat B Brier':13} | {'Strat C Brier':13} | {'Delta Brier':12} | {'Uncertainty':16}"
    print(header)
    print("-" * len(header))

    for r in exp.evaluation_results:
        b_a = f"{r.strategy_a_global.brier_score.value:.4f}" if r.strategy_a_global.brier_score.value is not None else "N/A"
        b_b = f"{r.strategy_b_local.brier_score.value:.4f}" if r.strategy_b_local.brier_score.value is not None else "N/A"
        b_c = f"{r.strategy_c_calibrated.brier_score.value:.4f}" if r.strategy_c_calibrated.brier_score.value is not None else "N/A"
        delta = f"{r.delta_brier_calib_vs_global:+.4f}"

        print(f"{r.held_out_application_id:16} | {r.budget_k:2} | {r.evaluation_sample_count:6} | {r.evaluation_failures_count:5} | {b_a:13} | {b_b:13} | {b_c:13} | {delta:12} | {r.uncertainty_level:16}")

    print("\n" + "=" * 80)
    print("ONLINE WALK-FORWARD CALIBRATION")
    print("=" * 80)
    for wf in exp.walk_forward_results:
        b_g = wf.global_metrics.brier_score.value or 0.0
        b_c = wf.calibrated_metrics.brier_score.value or 0.0
        pct_imprv = ((b_g - b_c) / b_g) * 100.0 if b_g > 0 else 0.0
        print(f"Application: {wf.held_out_application_id}")
        print(f"  Online Steps:     {wf.total_steps} (Fails: {wf.failures_observed}, Passes: {wf.passes_observed})")
        print(f"  Global Brier:     {b_g:.4f}")
        print(f"  Calibrated Brier: {b_c:.4f}  (Improvement: {pct_imprv:+.1f}%)")

    print("\n" + "=" * 80)
    print("SECONDARY FEATURE ABLATION ANALYSIS (K=3)")
    print("=" * 80)
    for ab in exp.feature_ablation_results:
        print(f"Application: {ab.held_out_application_id}")
        print(f"  Model A (All Features, 23):        Brier = {ab.model_a_all_features.brier_score:.4f}")
        print(f"  Model B (No Absolute Features, 21): Brier = {ab.model_b_no_absolute_features.brier_score:.4f}")
        print(f"  Model C (Relative Only, 10):        Brier = {ab.model_c_relative_only_features.brier_score:.4f}")
        print(f"  Finding: {ab.conclusion}")

    print("\n" + "=" * 80)
    print("FAILURE-CASE ANALYSIS (K=3 Natural Failures)")
    print("=" * 80)
    print(f"Total failures inspected: {len(exp.failure_analyses)}")
    for f in exp.failure_analyses:
        print(f"- Run: {f.run_id} | App: {f.application_id} | Test: {f.test_case_id}")
        print(f"  Global Prob:     {f.global_prob:.4f}")
        print(f"  Calibrated Prob: {f.calibrated_prob:.4f}")
        print(f"  Outcome:         Global={f.classification_outcome_global}, Calibrated={f.classification_outcome_calibrated}")
        print(f"  Telemetry Deterioration Detected: {f.preceding_telemetry_deterioration_detected}")
        print(f"  Details: {f.explanation}")

    print("\n" + "=" * 80)
    print("SCIENTIFIC HYPOTHESES VERDICTS")
    print("=" * 80)
    for h, v in exp.hypotheses_verdicts.items():
        print(f"  {h:35} : {v}")

    print("\n" + "=" * 80)
    print("EXECUTIVE SUMMARY")
    print("=" * 80)
    for line in exp.scientific_summary:
        print(f"* {line}")

    # Persist experiment JSON
    out_dir = "backend/data/experiments"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{exp.experiment_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(exp.model_dump_json(indent=2))
    print(f"\n[Saved full experiment report to: {out_file}]")
    print("=" * 80)


if __name__ == "__main__":
    main()
