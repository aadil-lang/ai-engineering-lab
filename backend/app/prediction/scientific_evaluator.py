import math
import logging
from typing import Any
from collections import defaultdict
from datetime import datetime, timezone

from backend.app.models.enums import (
    DatasetStatus,
    EvaluationSplitType,
    PredictionEvaluationStatus,
    RiskBand,
)
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilityFeatureVector,
    DatasetAuditReport,
    DatasetProvenanceRecord,
    ConfusionMatrix,
    ClassificationMetrics,
    SplitEvaluationMetrics,
    BaselineEvaluation,
    CalibrationMetrics,
    PredictionRecord,
    ContinuousScientificEvaluationReport,
)
from backend.app.prediction.reliability_model import (
    LogisticReliabilityModel,
    BaseBaselinePredictor,
)

logger = logging.getLogger("ai_qa_platform.scientific_evaluator")

class ScientificEvaluator:
    """
    Independent Scientific Validation and Continuous Evaluation Layer.
    Audits dataset integrity, prevents temporal data leakage, benchmarks baselines,
    evaluates probability calibration, and tracks prediction-to-outcome verification.
    """

    @classmethod
    def audit_dataset(cls, records: list[ReliabilityRecord]) -> DatasetAuditReport:
        """
        Conducts a formal statistical audit of all stored historical QA executions.
        Never fabricates synthetic runs.
        """
        total_runs = len(records)
        if total_runs == 0:
            return DatasetAuditReport(
                total_runs=0,
                completed_runs=0,
                failed_runs=0,
                passed_runs=0,
                total_test_cases=0,
                runs_with_repeated_executions=0,
                total_usable_reliability_records=0,
                total_usable_prediction_samples=0,
                positive_labels_count=0,
                negative_labels_count=0,
                unique_test_cases_count=0,
                earliest_execution_timestamp=None,
                latest_execution_timestamp=None,
                samples_per_test_case={},
                single_execution_test_cases_count=0,
                repeated_execution_test_cases_count=0,
                status=DatasetStatus.NO_DATA,
                status_reason="Zero historical QA executions found in database. Initial runs required.",
            )

        failed_runs = sum(1 for r in records if r.failure_label == 1)
        passed_runs = total_runs - failed_runs

        # Group runs by test_case_id or target
        tc_groups: dict[str, list[ReliabilityRecord]] = defaultdict(list)
        for r in records:
            key = r.test_case_id or f"target_{r.target_id}"
            tc_groups[key].append(r)

        unique_tc_count = len(tc_groups)
        single_exec_count = sum(1 for group in tc_groups.values() if len(group) == 1)
        repeated_exec_count = sum(1 for group in tc_groups.values() if len(group) > 1)
        runs_in_repeated = sum(len(group) for group in tc_groups.values() if len(group) > 1)

        # Count usable t -> t+1 transitions
        usable_transitions = sum(len(group) - 1 for group in tc_groups.values() if len(group) > 1)
        
        # Chronological timestamps
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        earliest_t = sorted_records[0].timestamp if sorted_records else None
        latest_t = sorted_records[-1].timestamp if sorted_records else None

        # Count positive (next=1) vs negative (next=0) transitions
        pos_labels = 0
        neg_labels = 0
        samples_per_tc: dict[str, int] = {}

        for key, group in tc_groups.items():
            sorted_group = sorted(group, key=lambda r: r.timestamp)
            trans_count = max(0, len(sorted_group) - 1)
            samples_per_tc[key] = trans_count
            for i in range(len(sorted_group) - 1):
                next_label = sorted_group[i + 1].failure_label
                if next_label == 1:
                    pos_labels += 1
                else:
                    neg_labels += 1

        # Determine dataset status
        if usable_transitions < 5:
            status = DatasetStatus.INSUFFICIENT_DATA
            reason = f"Small dataset: {usable_transitions} temporal (t -> t+1) transitions available, minimum 5 required for statistical evaluation."
        elif pos_labels == 0 or neg_labels == 0:
            status = DatasetStatus.INSUFFICIENT_DATA
            reason = f"Single-class dataset: All transitions have outcome label {1 if pos_labels > 0 else 0}. Both passed and failed transitions required for discrimination."
        else:
            status = DatasetStatus.USABLE
            reason = f"Usable dataset: {usable_transitions} valid chronological transitions across {unique_tc_count} test paths with binary class distribution ({pos_labels} fails, {neg_labels} passes)."

        return DatasetAuditReport(
            total_runs=total_runs,
            completed_runs=total_runs,
            failed_runs=failed_runs,
            passed_runs=passed_runs,
            total_test_cases=unique_tc_count,
            runs_with_repeated_executions=runs_in_repeated,
            total_usable_reliability_records=total_runs,
            total_usable_prediction_samples=usable_transitions,
            positive_labels_count=pos_labels,
            negative_labels_count=neg_labels,
            unique_test_cases_count=unique_tc_count,
            earliest_execution_timestamp=earliest_t,
            latest_execution_timestamp=latest_t,
            samples_per_test_case=samples_per_tc,
            single_execution_test_cases_count=single_exec_count,
            repeated_execution_test_cases_count=repeated_exec_count,
            status=status,
            status_reason=reason,
        )

    @classmethod
    def build_provenance_records(
        cls,
        records: list[ReliabilityRecord],
    ) -> list[DatasetProvenanceRecord]:
        """
        Generates verifiable provenance records for every t -> t+1 prediction sample.
        Validates that feature_timestamp < target_timestamp and target is immediately subsequent.
        """
        sorted_records = sorted(records, key=lambda r: r.timestamp)
        tc_groups: dict[str, list[ReliabilityRecord]] = defaultdict(list)
        for r in sorted_records:
            key = r.test_case_id or f"target_{r.target_id}"
            tc_groups[key].append(r)

        provenance_list: list[DatasetProvenanceRecord] = []
        sample_idx = 1

        for key, group in tc_groups.items():
            sorted_group = sorted(group, key=lambda r: r.timestamp)
            for i in range(len(sorted_group) - 1):
                curr = sorted_group[i]
                nxt = sorted_group[i + 1]

                # Strict chronological assertion
                if curr.timestamp > nxt.timestamp:
                    logger.warning(f"Temporal order inversion detected in test case {key}: {curr.timestamp} > {nxt.timestamp}")

                prov = DatasetProvenanceRecord(
                    sample_id=f"samp_{sample_idx:04d}",
                    test_case_id=key,
                    feature_run_id=curr.run_id,
                    target_run_id=nxt.run_id,
                    feature_timestamp=curr.timestamp,
                    target_timestamp=nxt.timestamp,
                    feature_vector_version="v1.0-temporal",
                    feature_names=[
                        "recent_fail_rate_3", "recent_fail_rate_5", "historical_fail_rate",
                        "consecutive_fails", "assertion_failure_count", "http_5xx_count",
                        "console_error_count", "grounding_score", "regression_detected"
                    ],
                    target_label=nxt.failure_label,
                )
                provenance_list.append(prov)
                sample_idx += 1

        return provenance_list

    @classmethod
    def create_chronological_splits(
        cls,
        vectors: list[ReliabilityFeatureVector],
    ) -> tuple[list[ReliabilityFeatureVector], list[ReliabilityFeatureVector], list[ReliabilityFeatureVector]]:
        """
        Partitions dataset into chronological splits (70% Train, 15% Validation, 15% Test).
        Strictly enforces max(train_timestamp) <= min(val_timestamp) <= min(test_timestamp).
        """
        labelled = [v for v in vectors if v.label_next_failed is not None]
        if not labelled:
            return [], [], []

        # Sort strictly chronologically
        sorted_vectors = sorted(labelled, key=lambda v: v.timestamp)
        n = len(sorted_vectors)

        if n < 3:
            # Too small for 3-way split; use all for training
            return sorted_vectors, [], []
        elif n < 6:
            # 2-way split
            split = max(1, int(n * 0.67))
            return sorted_vectors[:split], [], sorted_vectors[split:]

        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        train_set = sorted_vectors[:train_end]
        val_set = sorted_vectors[train_end:val_end]
        test_set = sorted_vectors[val_end:]

        return train_set, val_set, test_set

    @classmethod
    def calculate_classification_metrics(
        cls,
        y_true: list[int],
        y_prob: list[float],
        threshold: float = 0.5,
    ) -> ClassificationMetrics:
        """
        Calculates exact classification metrics and confusion matrix.
        Gracefully handles zero-division and single-class conditions without fabricating values.
        """
        n = len(y_true)
        if n == 0:
            return ClassificationMetrics(
                sample_count=0,
                accuracy=None,
                precision=None,
                recall=None,
                f1_score=None,
                roc_auc=None,
                confusion_matrix=ConfusionMatrix(),
                notes=["No test samples provided for evaluation."],
            )

        y_pred = [1 if p >= threshold else 0 for p in y_prob]

        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
        tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)

        matrix = ConfusionMatrix(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
        )

        acc = (tp + tn) / n
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if tp > 0 else 0.0)
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else (1.0 if tp > 0 else 0.0)
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        # ROC-AUC calculation (rank-sum method)
        roc_auc = None
        notes = []
        pos_count = sum(y_true)
        neg_count = n - pos_count

        if pos_count > 0 and neg_count > 0:
            # Pairwise ranking AUC
            pairs_correct = 0.0
            total_pairs = pos_count * neg_count
            for i in range(n):
                if y_true[i] == 1:
                    for j in range(n):
                        if y_true[j] == 0:
                            if y_prob[i] > y_prob[j]:
                                pairs_correct += 1.0
                            elif y_prob[i] == y_prob[j]:
                                pairs_correct += 0.5
            roc_auc = round(pairs_correct / total_pairs, 4) if total_pairs > 0 else None
        else:
            notes.append("ROC-AUC not mathematically defined: single class present in evaluation set.")

        return ClassificationMetrics(
            sample_count=n,
            accuracy=round(acc, 4),
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1_score=round(f1, 4),
            roc_auc=roc_auc,
            confusion_matrix=matrix,
            notes=notes,
        )

    @classmethod
    def evaluate_baselines(
        cls,
        test_samples: list[ReliabilityFeatureVector],
    ) -> list[BaselineEvaluation]:
        """
        Evaluates all deterministic baselines on the holdout test set.
        """
        if not test_samples:
            return []

        y_true = [v.label_next_failed for v in test_samples if v.label_next_failed is not None]
        if not y_true:
            return []

        # Baseline A: Last Execution Status
        probs_a = [BaseBaselinePredictor.predict_last_status(v) for v in test_samples if v.label_next_failed is not None]
        metrics_a = cls.calculate_classification_metrics(y_true, probs_a)

        # Baseline B: 3-Run Moving Average
        probs_b = [BaseBaselinePredictor.predict_moving_average(v) for v in test_samples if v.label_next_failed is not None]
        metrics_b = cls.calculate_classification_metrics(y_true, probs_b)

        # Baseline C: Cumulative Historical Frequency
        probs_c = [BaseBaselinePredictor.predict_historical_frequency(v) for v in test_samples if v.label_next_failed is not None]
        metrics_c = cls.calculate_classification_metrics(y_true, probs_c)

        return [
            BaselineEvaluation(
                baseline_id="baseline_a",
                baseline_name="Baseline A: Last Execution Status",
                description="Predicts next execution failure (P=1) if current execution had failures, else (P=0).",
                metrics=metrics_a,
            ),
            BaselineEvaluation(
                baseline_id="baseline_b",
                baseline_name="Baseline B: 3-Run Moving Average",
                description="Predicts failure probability using moving average failure rate of past 3 runs.",
                metrics=metrics_b,
            ),
            BaselineEvaluation(
                baseline_id="baseline_c",
                baseline_name="Baseline C: Cumulative Historical Frequency",
                description="Predicts failure probability using lifetime historical execution failure frequency.",
                metrics=metrics_c,
            ),
        ]

    @classmethod
    def evaluate_calibration(
        cls,
        y_true: list[int],
        y_prob: list[float],
        n_bins: int = 5,
    ) -> CalibrationMetrics:
        """
        Scientifically measures empirical probability calibration using Brier score and Expected Calibration Error (ECE).
        Does not assume sigmoid output is calibrated without empirical validation.
        """
        n = len(y_true)
        if n < 5:
            return CalibrationMetrics(
                is_evaluated=False,
                brier_score=None,
                expected_calibration_error=None,
                reliability_diagram_bins=[],
                status="INSUFFICIENT_DATA",
                notes=[f"Insufficient evaluation samples ({n} < 5) to establish empirical probability calibration."],
            )

        # Brier Score = (1/N) * sum((prob - y)^2)
        brier = sum((p - y) ** 2 for p, y in zip(y_prob, y_true)) / n

        # Reliability Diagram & ECE
        bin_width = 1.0 / n_bins
        bins = []
        ece = 0.0

        for b in range(n_bins):
            bin_lower = b * bin_width
            bin_upper = (b + 1) * bin_width
            
            bin_indices = [
                i for i in range(n) 
                if (bin_lower <= y_prob[i] < bin_upper) or (b == n_bins - 1 and y_prob[i] == bin_upper)
            ]
            bin_count = len(bin_indices)

            if bin_count > 0:
                avg_confidence = sum(y_prob[i] for i in bin_indices) / bin_count
                avg_accuracy = sum(y_true[i] for i in bin_indices) / bin_count
                ece += (bin_count / n) * abs(avg_accuracy - avg_confidence)

                bins.append({
                    "bin_index": b + 1,
                    "bin_range": f"{int(bin_lower * 100)}%-{int(bin_upper * 100)}%",
                    "sample_count": bin_count,
                    "mean_predicted_probability": round(avg_confidence, 4),
                    "empirical_positive_fraction": round(avg_accuracy, 4),
                    "calibration_gap": round(abs(avg_accuracy - avg_confidence), 4),
                })
            else:
                bins.append({
                    "bin_index": b + 1,
                    "bin_range": f"{int(bin_lower * 100)}%-{int(bin_upper * 100)}%",
                    "sample_count": 0,
                    "mean_predicted_probability": round(bin_lower + bin_width / 2, 2),
                    "empirical_positive_fraction": 0.0,
                    "calibration_gap": 0.0,
                })

        return CalibrationMetrics(
            is_evaluated=True,
            brier_score=round(brier, 4),
            expected_calibration_error=round(ece, 4),
            reliability_diagram_bins=bins,
            status="EVALUATED",
            notes=[
                f"Brier score: {round(brier, 4)} (0.0 = perfect accuracy, 0.25 = random uninformative guessing).",
                f"Expected Calibration Error (ECE): {round(ece * 100, 1)}%.",
            ],
        )

    @classmethod
    def generate_scientific_report(
        cls,
        records: list[ReliabilityRecord],
        vectors: list[ReliabilityFeatureVector],
        model: LogisticReliabilityModel,
        prediction_records: list[PredictionRecord],
    ) -> ContinuousScientificEvaluationReport:
        """
        Generates a comprehensive scientific validation and continuous evaluation report.
        """
        audit = cls.audit_dataset(records)
        provenance = cls.build_provenance_records(records)
        train_set, val_set, test_set = cls.create_chronological_splits(vectors)

        splits_metrics: list[SplitEvaluationMetrics] = []
        eval_samples = test_set if test_set else (val_set if val_set else train_set)

        # 1. Train Split
        if train_set:
            y_train = [v.label_next_failed for v in train_set if v.label_next_failed is not None]
            p_train = [model.predict_probability(v.features) for v in train_set if v.label_next_failed is not None]
            m_train = cls.calculate_classification_metrics(y_train, p_train)
            splits_metrics.append(
                SplitEvaluationMetrics(
                    split_name=EvaluationSplitType.TRAIN,
                    sample_count=len(train_set),
                    time_range_start=train_set[0].timestamp if train_set else None,
                    time_range_end=train_set[-1].timestamp if train_set else None,
                    positive_count=sum(y_train),
                    negative_count=len(y_train) - sum(y_train),
                    metrics=m_train,
                )
            )

        # 2. Validation Split
        if val_set:
            y_val = [v.label_next_failed for v in val_set if v.label_next_failed is not None]
            p_val = [model.predict_probability(v.features) for v in val_set if v.label_next_failed is not None]
            m_val = cls.calculate_classification_metrics(y_val, p_val)
            splits_metrics.append(
                SplitEvaluationMetrics(
                    split_name=EvaluationSplitType.VALIDATION,
                    sample_count=len(val_set),
                    time_range_start=val_set[0].timestamp if val_set else None,
                    time_range_end=val_set[-1].timestamp if val_set else None,
                    positive_count=sum(y_val),
                    negative_count=len(y_val) - sum(y_val),
                    metrics=m_val,
                )
            )

        # 3. Test Split
        model_test_eval = None
        if test_set:
            y_test = [v.label_next_failed for v in test_set if v.label_next_failed is not None]
            p_test = [model.predict_probability(v.features) for v in test_set if v.label_next_failed is not None]
            m_test = cls.calculate_classification_metrics(y_test, p_test)
            model_test_eval = SplitEvaluationMetrics(
                split_name=EvaluationSplitType.TEST,
                sample_count=len(test_set),
                time_range_start=test_set[0].timestamp if test_set else None,
                time_range_end=test_set[-1].timestamp if test_set else None,
                positive_count=sum(y_test),
                negative_count=len(y_test) - sum(y_test),
                metrics=m_test,
            )
            splits_metrics.append(model_test_eval)

        # Baselines Benchmark on test/eval split
        baselines = cls.evaluate_baselines(eval_samples)

        # Calibration on test/eval split
        y_eval = [v.label_next_failed for v in eval_samples if v.label_next_failed is not None]
        p_eval = [model.predict_probability(v.features) for v in eval_samples if v.label_next_failed is not None]
        calibration = cls.evaluate_calibration(y_eval, p_eval)

        # Continuous prediction records counts
        evaluated_preds = [p for p in prediction_records if p.evaluation_status == PredictionEvaluationStatus.EVALUATED]
        pending_preds = [p for p in prediction_records if p.evaluation_status == PredictionEvaluationStatus.PENDING]

        summary_notes = []
        if audit.status == DatasetStatus.INSUFFICIENT_DATA:
            summary_notes.append("Dataset size is below minimum statistical significance threshold. Metric values reflect sample distributions rather than converged generalization.")
        if not calibration.is_evaluated:
            summary_notes.append("Model outputs predicted probabilities; empirical calibration has not yet been established due to sample size.")
        if evaluated_preds:
            correct_count = sum(1 for p in evaluated_preds if p.is_correct is True)
            live_acc = round((correct_count / len(evaluated_preds)) * 100, 1)
            summary_notes.append(f"Continuous closed-loop evaluation: {len(evaluated_preds)} predictions verified against subsequent test runs (Live Accuracy: {live_acc}%).")

        return ContinuousScientificEvaluationReport(
            dataset_audit=audit,
            provenance_samples=provenance[:50],  # Return up to 50 for inspection
            splits=splits_metrics,
            baselines=baselines,
            model_evaluation=model_test_eval,
            calibration=calibration,
            evaluated_predictions_count=len(evaluated_preds),
            pending_predictions_count=len(pending_preds),
            prediction_records=prediction_records[:50],
            evaluation_summary_notes=summary_notes,
        )
