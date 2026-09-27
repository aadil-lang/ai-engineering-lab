import math
import logging
from typing import Any
from collections import Counter, defaultdict
from datetime import datetime, timezone

from backend.app.models.enums import (
    ExecutionSource,
    PopulationType,
    DatasetStatus,
    EvaluationSplitType,
    RiskBand,
    CampaignType,
)
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilityFeatureVector,
    ClassificationMetrics,
    ConfusionMatrix,
    PopulationAuditSummary,
    WalkForwardFoldMetric,
    WalkForwardModelAggregate,
    WalkForwardEvaluationReport,
    PopulationSeparationReport,
)
from backend.app.prediction.reliability_model import (
    LogisticReliabilityModel,
    ScaledLogisticReliabilityModel,
    WeightedLogisticReliabilityModel,
    BaseBaselinePredictor,
)
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor

logger = logging.getLogger("ai_qa_platform.walk_forward_evaluator")

POPULATION_DEFINITIONS: dict[PopulationType, dict[str, Any]] = {
    PopulationType.ALL_HISTORICAL: {
        "name": "Population A: All Historical Executions",
        "description": "Complete unfiltered dataset containing all genuine QA executions, including real browser, AI agent, mock experiments, and demo shop harness sequences.",
        "sources": [
            ExecutionSource.REAL_PLAYWRIGHT,
            ExecutionSource.REAL_AI_AGENT,
            ExecutionSource.CONTROLLED_DEFECT,
            ExecutionSource.SYNTHETIC_MOCK,
            ExecutionSource.DEMO_HARNESS,
            ExecutionSource.UNKNOWN,
        ],
    },
    PopulationType.REAL_EXECUTIONS_ONLY: {
        "name": "Population B: Real Browser & AI Agent Executions",
        "description": "Exclusively real browser executions (Playwright) and real LLM browser agent executions against real application targets, excluding mock and demo harness artifacts.",
        "sources": [
            ExecutionSource.REAL_PLAYWRIGHT,
            ExecutionSource.REAL_AI_AGENT,
        ],
    },
    PopulationType.REAL_PLAYWRIGHT_ONLY: {
        "name": "Population C: Real Playwright Browser Executions",
        "description": "Strictly deterministic Playwright browser test executions against real application targets.",
        "sources": [
            ExecutionSource.REAL_PLAYWRIGHT,
        ],
    },
    PopulationType.REAL_AI_AGENT_ONLY: {
        "name": "Population D: Real AI Agent Executions",
        "description": "Autonomous browser agent executions driven by local LLMs (Qwen/Ollama) on live applications.",
        "sources": [
            ExecutionSource.REAL_AI_AGENT,
        ],
    },
    PopulationType.CONTROLLED_AND_DEMO: {
        "name": "Population E: Controlled Defect & Demo Harness",
        "description": "Deliberately controlled defect injection experiments, synthetic mock runners, and alternating demo shop sequences.",
        "sources": [
            ExecutionSource.CONTROLLED_DEFECT,
            ExecutionSource.DEMO_HARNESS,
            ExecutionSource.SYNTHETIC_MOCK,
        ],
    },
}


class PopulationSeparator:
    """
    Separates reliability datasets into distinct operational populations
    to prevent population contamination and misleading cross-environment generalization.
    """

    @classmethod
    def filter_records_by_population(
        cls,
        records: list[ReliabilityRecord],
        population: PopulationType,
    ) -> list[ReliabilityRecord]:
        allowed_sources = set(POPULATION_DEFINITIONS[population]["sources"])
        res = []
        for r in records:
            if population == PopulationType.ALL_HISTORICAL:
                res.append(r)
            elif population in (
                PopulationType.REAL_EXECUTIONS_ONLY,
                PopulationType.REAL_PLAYWRIGHT_ONLY,
                PopulationType.REAL_AI_AGENT_ONLY,
            ):
                if r.execution_source not in allowed_sources:
                    continue
                if r.campaign_type is not None and r.campaign_type != CampaignType.REAL_RELIABILITY:
                    continue
                res.append(r)
            elif population == PopulationType.CONTROLLED_AND_DEMO:
                if r.campaign_type == CampaignType.REAL_RELIABILITY:
                    continue
                if r.campaign_type in (CampaignType.DEMO, CampaignType.CONTROLLED_EXPERIMENT, CampaignType.SYNTHETIC) or r.execution_source in allowed_sources:
                    res.append(r)
        return res

    @classmethod
    def filter_vectors_by_population(
        cls,
        vectors: list[ReliabilityFeatureVector],
        population: PopulationType,
    ) -> list[ReliabilityFeatureVector]:
        allowed_sources = set(POPULATION_DEFINITIONS[population]["sources"])
        res = []
        for v in vectors:
            if population == PopulationType.ALL_HISTORICAL:
                res.append(v)
            elif population in (
                PopulationType.REAL_EXECUTIONS_ONLY,
                PopulationType.REAL_PLAYWRIGHT_ONLY,
                PopulationType.REAL_AI_AGENT_ONLY,
            ):
                if v.execution_source not in allowed_sources:
                    continue
                if v.target_execution_source is not None and v.target_execution_source not in allowed_sources:
                    continue
                if v.campaign_type is not None and v.campaign_type != CampaignType.REAL_RELIABILITY:
                    continue
                if v.target_campaign_type is not None and v.target_campaign_type != CampaignType.REAL_RELIABILITY:
                    continue
                res.append(v)
            elif population == PopulationType.CONTROLLED_AND_DEMO:
                if v.campaign_type == CampaignType.REAL_RELIABILITY or v.target_campaign_type == CampaignType.REAL_RELIABILITY:
                    continue
                if (v.campaign_type in (CampaignType.DEMO, CampaignType.CONTROLLED_EXPERIMENT, CampaignType.SYNTHETIC) or v.execution_source in allowed_sources) and \
                   (v.target_campaign_type is None or v.target_campaign_type in (CampaignType.DEMO, CampaignType.CONTROLLED_EXPERIMENT, CampaignType.SYNTHETIC) or v.target_execution_source in allowed_sources):
                    res.append(v)
        return res


    @classmethod
    def audit_population(
        cls,
        population: PopulationType,
        records: list[ReliabilityRecord],
        vectors: list[ReliabilityFeatureVector],
    ) -> PopulationAuditSummary:
        pop_def = POPULATION_DEFINITIONS[population]
        pop_records = cls.filter_records_by_population(records, population)
        pop_vectors = cls.filter_vectors_by_population(vectors, population)

        usable_transitions = [v for v in pop_vectors if v.label_next_failed is not None]
        total_transitions = len(usable_transitions)
        pos_count = sum(1 for v in usable_transitions if v.label_next_failed == 1)
        neg_count = sum(1 for v in usable_transitions if v.label_next_failed == 0)
        failure_rate = (pos_count / total_transitions) if total_transitions > 0 else 0.0

        if total_transitions == 0:
            status = DatasetStatus.NO_DATA
            reason = "Zero usable temporal transitions available in this execution population."
        elif total_transitions < 10:
            status = DatasetStatus.INSUFFICIENT_DATA
            reason = f"Small population sample size: {total_transitions} transitions available (minimum 10 required for statistically sound evaluation)."
        elif pos_count == 0 or neg_count == 0:
            status = DatasetStatus.INSUFFICIENT_DATA
            reason = f"Single-class population: All {total_transitions} transitions have outcome label {1 if pos_count > 0 else 0}. Multi-class outcomes required for predictive evaluation."
        else:
            status = DatasetStatus.USABLE
            reason = f"Usable population: {total_transitions} transitions ({pos_count} fails, {neg_count} passes, {failure_rate:.1%} failure rate)."

        return PopulationAuditSummary(
            population_id=population,
            population_name=pop_def["name"],
            description=pop_def["description"],
            total_runs=len(pop_records),
            total_transitions=total_transitions,
            failures_count=pos_count,
            passes_count=neg_count,
            failure_rate=round(failure_rate, 4),
            status=status,
            status_reason=reason,
            included_sources=pop_def["sources"],
        )


class WalkForwardEvaluator:
    """
    Expanding-window walk-forward temporal cross-validation engine.
    Ensures models are strictly evaluated on unseen future time slices without lookahead bias.
    """

    @classmethod
    def evaluate_metrics(
        cls,
        y_true: list[int],
        y_pred: list[int],
        y_probs: list[float],
    ) -> tuple[ClassificationMetrics, float, float]:
        """Calculates standard classification metrics, Brier score, and ECE."""
        n = len(y_true)
        if n == 0:
            return ClassificationMetrics(), 0.0, 0.0

        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
        tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)

        accuracy = (tp + tn) / n
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # ROC-AUC via rank sum / Mann-Whitney
        pos_indices = [i for i, y in enumerate(y_true) if y == 1]
        neg_indices = [i for i, y in enumerate(y_true) if y == 0]
        n_pos = len(pos_indices)
        n_neg = len(neg_indices)

        if n_pos > 0 and n_neg > 0:
            paired = sorted(enumerate(y_probs), key=lambda x: x[1])
            ranks = {orig_idx: rank + 1 for rank, (orig_idx, _) in enumerate(paired)}
            sum_ranks_pos = sum(ranks[idx] for idx in pos_indices)
            u = sum_ranks_pos - (n_pos * (n_pos + 1)) / 2.0
            roc_auc = u / (n_pos * n_neg)
        else:
            roc_auc = 0.5

        # Brier Score
        brier = sum((p - y) ** 2 for p, y in zip(y_probs, y_true)) / n

        # Expected Calibration Error (ECE) with 5 bins
        bin_count = 5
        bins: list[list[tuple[float, int]]] = [[] for _ in range(bin_count)]
        for p, y in zip(y_probs, y_true):
            b_idx = min(int(p * bin_count), bin_count - 1)
            bins[b_idx].append((p, y))

        ece = 0.0
        for b in bins:
            if b:
                avg_conf = sum(item[0] for item in b) / len(b)
                avg_acc = sum(item[1] for item in b) / len(b)
                ece += (len(b) / n) * abs(avg_acc - avg_conf)

        cm = ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
        )

        metrics = ClassificationMetrics(
            sample_count=n,
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            roc_auc=round(roc_auc, 4),
            confusion_matrix=cm,
        )

        return metrics, round(brier, 4), round(ece, 4)

    @classmethod
    def run_walk_forward_evaluation(
        cls,
        vectors: list[ReliabilityFeatureVector],
        population: PopulationType = PopulationType.ALL_HISTORICAL,
        min_train_size: int = 20,
        step_size: int = 5,
    ) -> WalkForwardEvaluationReport:
        pop_def = POPULATION_DEFINITIONS[population]
        pop_vectors = PopulationSeparator.filter_vectors_by_population(vectors, population)

        # Usable chronological transitions
        transitions = [v for v in pop_vectors if v.label_next_failed is not None]
        transitions.sort(key=lambda v: v.timestamp)
        n_total = len(transitions)

        if n_total < min_train_size + step_size:
            return WalkForwardEvaluationReport(
                population=population,
                population_name=pop_def["name"],
                total_samples=n_total,
                min_train_size=min_train_size,
                step_size=step_size,
                num_folds=0,
                status="INSUFFICIENT_DATA",
                status_reason=f"Insufficient chronological samples for walk-forward validation: {n_total} transitions available, minimum {min_train_size + step_size} required (min train {min_train_size} + test step {step_size}).",
                folds=[],
                model_aggregates=[],
                scientific_conclusions=[
                    f"Population {population.value} contains {n_total} transitions, which is below the threshold for expanding window cross-validation.",
                    "Additional genuine executions are required before walk-forward generalization can be statistically evaluated on this subset.",
                ],
            )

        folds: list[WalkForwardFoldMetric] = []
        model_fold_metrics: dict[str, list[ClassificationMetrics]] = defaultdict(list)
        model_fold_brier: dict[str, list[float]] = defaultdict(list)
        model_fold_ece: dict[str, list[float]] = defaultdict(list)

        fold_idx = 0
        train_end = min_train_size

        while train_end + step_size <= n_total:
            test_start = train_end
            test_end = min(test_start + step_size, n_total)
            train_set = transitions[:train_end]
            test_set = transitions[test_start:test_end]

            if not test_set:
                break

            train_fails = sum(1 for v in train_set if v.label_next_failed == 1)
            train_prev = train_fails / len(train_set)
            test_fails = sum(1 for v in test_set if v.label_next_failed == 1)
            test_prev = test_fails / len(test_set)
            y_test = [v.label_next_failed for v in test_set if v.label_next_failed is not None]

            # Model 1: v1.0 (Fixed weights / unscaled baseline)
            m_v1_0 = LogisticReliabilityModel()
            probs_v1_0 = [m_v1_0.predict_failure_probability(v.features) for v in test_set]
            preds_v1_0 = [1 if p >= 0.5 else 0 for p in probs_v1_0]
            met_v1_0, brier_v1_0, ece_v1_0 = cls.evaluate_metrics(y_test, preds_v1_0, probs_v1_0)

            # Model 2: v1.1 (Scaled Logistic Regression fitted strictly on train_set)
            m_v1_1 = ScaledLogisticReliabilityModel()
            m_v1_1.fit(train_set)
            probs_v1_1 = [m_v1_1.predict_failure_probability(v.features) for v in test_set]
            preds_v1_1 = [1 if p >= 0.5 else 0 for p in probs_v1_1]
            met_v1_1, brier_v1_1, ece_v1_1 = cls.evaluate_metrics(y_test, preds_v1_1, probs_v1_1)

            # Model 3: v1.2 (Weighted Logistic Regression fitted strictly on train_set)
            m_v1_2 = WeightedLogisticReliabilityModel()
            m_v1_2.fit(train_set)
            probs_v1_2 = [m_v1_2.predict_failure_probability(v.features) for v in test_set]
            preds_v1_2 = [1 if p >= 0.5 else 0 for p in probs_v1_2]
            met_v1_2, brier_v1_2, ece_v1_2 = cls.evaluate_metrics(y_test, preds_v1_2, probs_v1_2)

            # Baseline: Majority Class
            preds_maj = [BaseBaselinePredictor.predict_majority_class(train_set) for _ in test_set]
            probs_maj = [float(p) for p in preds_maj]
            met_maj, brier_maj, _ = cls.evaluate_metrics(y_test, preds_maj, probs_maj)

            # Baseline: Historical Prevalence
            prob_prev_val = BaseBaselinePredictor.predict_historical_prevalence(train_set)
            probs_prev = [prob_prev_val for _ in test_set]
            preds_prev = [1 if p >= 0.5 else 0 for p in probs_prev]
            met_prev, brier_prev, _ = cls.evaluate_metrics(y_test, preds_prev, probs_prev)

            # Baseline: Random Reproducible
            probs_rand = [BaseBaselinePredictor.predict_random_probability(seed=42 + fold_idx * 100 + i) for i in range(len(test_set))]
            preds_rand = [1 if p >= 0.5 else 0 for p in probs_rand]
            met_rand, brier_rand, _ = cls.evaluate_metrics(y_test, preds_rand, probs_rand)

            fold_models_map = {
                "v1.0": met_v1_0,
                "v1.1": met_v1_1,
                "v1.2": met_v1_2,
                "majority_baseline": met_maj,
                "prevalence_baseline": met_prev,
                "random_baseline": met_rand,
            }
            fold_brier_map = {
                "v1.0": brier_v1_0,
                "v1.1": brier_v1_1,
                "v1.2": brier_v1_2,
                "majority_baseline": brier_maj,
                "prevalence_baseline": brier_prev,
                "random_baseline": brier_rand,
            }

            for mk, mv in fold_models_map.items():
                model_fold_metrics[mk].append(mv)
            for mk, bv in fold_brier_map.items():
                model_fold_brier[mk].append(bv)
            model_fold_ece["v1.0"].append(ece_v1_0)
            model_fold_ece["v1.1"].append(ece_v1_1)
            model_fold_ece["v1.2"].append(ece_v1_2)

            folds.append(
                WalkForwardFoldMetric(
                    fold_index=fold_idx,
                    train_start_timestamp=train_set[0].timestamp,
                    train_end_timestamp=train_set[-1].timestamp,
                    test_start_timestamp=test_set[0].timestamp,
                    test_end_timestamp=test_set[-1].timestamp,
                    train_sample_count=len(train_set),
                    test_sample_count=len(test_set),
                    train_failure_rate=round(train_prev, 4),
                    test_failure_rate=round(test_prev, 4),
                    model_metrics=fold_models_map,
                    brier_scores=fold_brier_map,
                )
            )

            fold_idx += 1
            train_end += step_size

        # Compute Aggregates across folds
        def compute_mean_std(values: list[float | None]) -> tuple[float | None, float | None]:
            valid = [v for v in values if v is not None]
            if not valid:
                return None, None
            mean_val = sum(valid) / len(valid)
            var = sum((x - mean_val) ** 2 for x in valid) / len(valid)
            std_val = math.sqrt(var)
            return round(mean_val, 4), round(std_val, 4)

        model_names = {
            "v1.0": "Logistic Reliability Model v1.0 (Fixed Prior)",
            "v1.1": "Scaled Logistic Model v1.1 (StandardScaler)",
            "v1.2": "Weighted Logistic Model v1.2 (Class-Weighted)",
            "majority_baseline": "Majority Class Baseline",
            "prevalence_baseline": "Historical Prevalence Baseline",
            "random_baseline": "Random Probability Baseline (Seed 42)",
        }

        aggregates: list[WalkForwardModelAggregate] = []
        for mid, mname in model_names.items():
            mets = model_fold_metrics[mid]
            briers = model_fold_brier[mid]
            eces = model_fold_ece.get(mid, [])

            acc_mean, acc_std = compute_mean_std([m.accuracy for m in mets])
            brier_mean, brier_std = compute_mean_std(briers)
            roc_mean, roc_std = compute_mean_std([m.roc_auc for m in mets])
            f1_mean, f1_std = compute_mean_std([m.f1_score for m in mets])
            ece_mean, ece_std = compute_mean_std(eces) if eces else (None, None)

            aggregates.append(
                WalkForwardModelAggregate(
                    model_id=mid,
                    model_name=mname,
                    mean_accuracy=acc_mean,
                    std_accuracy=acc_std,
                    mean_brier_score=brier_mean,
                    std_brier_score=brier_std,
                    mean_roc_auc=roc_mean,
                    std_roc_auc=roc_std,
                    mean_f1=f1_mean,
                    std_f1=f1_std,
                    mean_ece=ece_mean,
                    std_ece=ece_std,
                )
            )

        # Scientific conclusions
        conclusions = [
            f"Walk-forward evaluation conducted across {len(folds)} expanding chronological folds (min train: {min_train_size}, step: {step_size}).",
            "Expanding window testing eliminates temporal lookahead bias and single-split boundary anomalies.",
        ]
        if aggregates:
            best_acc = max((a for a in aggregates if a.mean_accuracy is not None), key=lambda x: x.mean_accuracy or 0.0, default=None)
            best_brier = min((a for a in aggregates if a.mean_brier_score is not None), key=lambda x: x.mean_brier_score or 1.0, default=None)
            if best_acc and best_brier:
                conclusions.append(
                    f"Across walk-forward folds, {best_acc.model_name} achieved highest mean accuracy ({best_acc.mean_accuracy:.1%} ± {best_acc.std_accuracy or 0.0:.1%})."
                )
                conclusions.append(
                    f"Lowest (best) mean Brier score across expanding windows was achieved by {best_brier.model_name} ({best_brier.mean_brier_score:.4f} ± {best_brier.std_brier_score or 0.0:.4f})."
                )

        return WalkForwardEvaluationReport(
            population=population,
            population_name=pop_def["name"],
            total_samples=n_total,
            min_train_size=min_train_size,
            step_size=step_size,
            num_folds=len(folds),
            status="EVALUATED" if folds else "INSUFFICIENT_DATA",
            status_reason=f"Successfully evaluated across {len(folds)} expanding chronological folds." if folds else "Insufficient data for folds.",
            folds=folds,
            model_aggregates=aggregates,
            scientific_conclusions=conclusions,
        )


class ProductionReliabilityDatasetAnalyzer:
    """
    High-level analyzer producing the complete Slice 6.4 Population Separation
    and Walk-Forward Evaluation Report.
    """

    @classmethod
    def generate_population_separation_report(
        cls,
        records: list[ReliabilityRecord],
        vectors: list[ReliabilityFeatureVector],
        min_train_size: int = 20,
        step_size: int = 5,
    ) -> PopulationSeparationReport:
        source_counts = Counter(r.execution_source.value for r in records)

        # Audit each of the 5 populations
        pop_summaries: list[PopulationAuditSummary] = []
        walk_forward_reports: dict[str, WalkForwardEvaluationReport] = {}

        for pop_type in PopulationType:
            summary = PopulationSeparator.audit_population(pop_type, records, vectors)
            pop_summaries.append(summary)

            wf_report = WalkForwardEvaluator.run_walk_forward_evaluation(
                vectors=vectors,
                population=pop_type,
                min_train_size=min_train_size,
                step_size=step_size,
            )
            walk_forward_reports[pop_type.value] = wf_report

        # Primary insights
        insights = [
            f"Execution Provenance Breakdown: {dict(source_counts)} across {len(records)} total QA runs.",
            "Population Separation prevents the alternating demo-shop test harness from contaminating real application reliability analytics.",
            "Real Browser & AI Agent executions (Population B) represent genuine software performance, while Population E reflects controlled defect injection cycles.",
            "Walk-Forward cross-validation provides variance-aware generalization estimates compared to static single-split evaluation.",
        ]

        return PopulationSeparationReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_runs=len(records),
            total_transitions=len([v for v in vectors if v.label_next_failed is not None]),
            source_breakdown=dict(source_counts),
            populations=pop_summaries,
            walk_forward_reports=walk_forward_reports,
            primary_insights=insights,
        )
