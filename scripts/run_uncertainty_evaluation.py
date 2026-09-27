#!/usr/bin/env python
"""
Slice 7.1 CLI Runner: Uncertainty-Aware Cold-Start Reliability & Decision Utility.

Executes the uncertainty evaluation against the live database:
- Derives mathematical posterior uncertainty bounds via Fisher information parameter covariance and Empirical Bayes shrinkage
- Evaluates cold-start uncertainty across K in {0, 1, 3, 5, 10}
- Evaluates selective prediction and abstention policies fitted strictly on training applications
- Stratifies predictions across LOW, MEDIUM, and HIGH uncertainty buckets
- Generates risk-coverage curves
- Evaluates deterministic scientific verdicts for H1-H5
"""

import sys
import os
import json

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.prediction.uncertainty_evaluator import UncertaintyEvaluator


def main():
    # Set stdout encoding safely
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 80)
    print("SLICE 7.1 — UNCERTAINTY-AWARE COLD-START RELIABILITY & DECISION UTILITY")
    print("=" * 80)

    db_path = "backend/data/reliability_platform.db"
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} not found.")
        sys.exit(1)

    parent_snap = "backend/data/snapshots/eval_snap_slice_7_0.json"
    if not os.path.exists(parent_snap):
        print(f"Error: Parent snapshot {parent_snap} not found. Slice 7.0 must be present.")
        sys.exit(1)

    print(f"\n[1/5] Verified parent snapshot: {parent_snap} (Slice 7.0 Frozen)")
    print("[2/5] Running UncertaintyEvaluator against live longitudinal database...")

    experiment = UncertaintyEvaluator.run_full_evaluation()

    print("\n" + "=" * 80)
    print("EXPERIMENT OVERVIEW & AUDIT PROVENANCE")
    print("=" * 80)
    print(f"Experiment ID:          {experiment.experiment_id}")
    print(f"Created At:             {experiment.created_at}")
    print(f"Parent Snapshot:        {experiment.parent_snapshot_id} (Slice 7.0 Frozen)")
    print(f"Snapshot ID:            {experiment.snapshot_id}")
    print(f"Protocol:               {experiment.protocol_version}")
    print(f"Model Version:          {experiment.model_version}")
    print(f"Uncertainty Method:     {experiment.uncertainty_method_version}")
    print(f"Decision Policy:        {experiment.decision_policy_version}")
    print(f"Evaluated Applications: {', '.join(experiment.test_applications)}")
    print(f"Total Evaluated Preds:  {experiment.total_eval_predictions}")

    print("\n" + "=" * 80)
    print("TABLE 1: COLD-START PREDICTIVE UNCERTAINTY ACROSS LOCAL BUDGET K")
    print("=" * 80)
    header = f"{'Held-Out App':<16} {'K':<4} {'N':<4} {'Fails':<6} {'Mean P':<8} {'Mean U':<8} {'Med U':<8} {'Brier':<8} {'Sel Brier':<10} {'Abstain %':<10}"
    print(header)
    print("-" * len(header))
    for res in experiment.cold_start_results:
        print(
            f"{res.application_id:<16} "
            f"K={res.budget_k:<2} "
            f"{res.prediction_count:<4} "
            f"{res.observed_failures:<6} "
            f"{res.mean_predicted_prob:<8.4f} "
            f"{res.mean_uncertainty:<8.4f} "
            f"{res.median_uncertainty:<8.4f} "
            f"{res.brier_score:<8.4f} "
            f"{res.selective_brier_default_policy:<10.4f} "
            f"{res.abstention_rate_default_policy * 100:<9.1f}%"
        )

    print("\n" + "=" * 80)
    print("TABLE 2: UNCERTAINTY-STRATIFIED CALIBRATION BUCKETS (H2 TESTING)")
    print("=" * 80)
    b_header = f"{'Bucket':<8} {'Range [Low, High]':<20} {'Samples':<8} {'Fails':<6} {'Mean U':<8} {'Mean P':<8} {'Fail Rate':<10} {'Brier Score':<12} {'MAE':<8}"
    print(b_header)
    print("-" * len(b_header))
    for b in experiment.uncertainty_buckets:
        print(
            f"{b.bucket_level.value:<8} "
            f"[{b.lower_bound:.3f}, {b.upper_bound:.3f}]{'':<7} "
            f"{b.sample_count:<8} "
            f"{b.failure_count:<6} "
            f"{b.mean_uncertainty:<8.4f} "
            f"{b.mean_predicted_prob:<8.4f} "
            f"{b.observed_failure_rate * 100:<9.1f}% "
            f"{b.brier_score:<12.4f} "
            f"{b.mean_absolute_error:<8.4f}"
        )

    print("\n" + "=" * 80)
    print("TABLE 3: SELECTIVE DECISION POLICIES (TRAINING-DERIVED THRESHOLDS)")
    print("=" * 80)
    p_header = f"{'Policy':<22} {'Tau':<6} {'Test App':<16} {'Coverage':<10} {'Abstain %':<10} {'Acc Fails':<10} {'Acc Brier':<10} {'Overall Brier':<14} {'Delta Brier':<12}"
    print(p_header)
    print("-" * len(p_header))
    for pol_res in experiment.selective_results:
        print(
            f"{pol_res.policy_id:<22} "
            f"{pol_res.threshold_tau:<6.3f} "
            f"{pol_res.test_application_id:<16} "
            f"{pol_res.test_coverage * 100:<9.1f}% "
            f"{pol_res.test_abstention_rate * 100:<9.1f}% "
            f"{pol_res.accepted_failures_count:<10} "
            f"{pol_res.accepted_brier_score:<10.4f} "
            f"{pol_res.overall_brier_score:<14.4f} "
            f"{pol_res.selective_brier_improvement:+11.4f}"
        )

    print("\n" + "=" * 80)
    print("TABLE 4: RISK-COVERAGE TRADE-OFF CURVE")
    print("=" * 80)
    rc_header = f"{'Target Coverage':<16} {'Accepted N':<12} {'Tau Cutoff':<12} {'Selective Brier':<16} {'Baseline Brier':<16} {'Selective MAE':<14}"
    print(rc_header)
    print("-" * len(rc_header))
    for rc in experiment.risk_coverage_curve:
        print(
            f"{rc.coverage * 100:<15.1f}% "
            f"{rc.accepted_count:<12} "
            f"{rc.threshold_tau:<12.4f} "
            f"{rc.selective_brier:<16.4f} "
            f"{rc.baseline_random_brier:<16.4f} "
            f"{rc.selective_mae:<14.4f}"
        )

    print("\n" + "=" * 80)
    print("TABLE 5: COVARIATE SHIFT VS INITIAL PREDICTIVE UNCERTAINTY (H5)")
    print("=" * 80)
    s_header = f"{'Application':<16} {'Std Shift':<12} {'Raw Shift':<12} {'Rel Shift':<12} {'Mean U (K=0)':<14} {'Mean U (K=5)':<14} {'Delta U':<10}"
    print(s_header)
    print("-" * len(s_header))
    for sh in experiment.shift_uncertainty_analysis:
        print(
            f"{sh.application_id:<16} "
            f"{sh.standardized_shift_mean:<11.2f}σ "
            f"{sh.raw_shift_mean:<11.2f}σ "
            f"{sh.relative_shift_mean:<11.2f}σ "
            f"{sh.mean_uncertainty_k0:<14.4f} "
            f"{sh.mean_uncertainty_k5:<14.4f} "
            f"{sh.uncertainty_reduction_k0_to_k5:<10.4f}"
        )

    print("\n" + "=" * 80)
    print("SCIENTIFIC HYPOTHESES EVALUATION & DETERMINISTIC VERDICTS")
    print("=" * 80)
    for v in experiment.hypotheses_verdicts:
        print(f"[{v.hypothesis_id}] {v.title}")
        print(f"     Verdict:     {v.verdict.value}")
        print(f"     Metric:      {v.empirical_metric_name} = {v.empirical_metric_value}")
        print(f"     Criterion:   {v.threshold_criterion}")
        print(f"     Finding:     {v.description}")
        print()

    print("=" * 80)
    print("SCIENTIFIC CONCLUSIONS")
    print("=" * 80)
    for idx, c in enumerate(experiment.scientific_summary, 1):
        print(f"  {idx}. {c}")
    print()
    print("Slice 7.1 uncertainty evaluation execution completed successfully.")


if __name__ == "__main__":
    main()
