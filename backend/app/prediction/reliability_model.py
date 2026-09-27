import math
import logging
from typing import Any
from datetime import datetime, timezone

from backend.app.models.enums import RiskBand, PredictionStatus
from backend.app.models.reliability import (
    ReliabilityFeatureVector,
    TestCasePrediction,
    FeatureImportance,
    ModelEvaluationMetrics,
)

logger = logging.getLogger("ai_qa_platform.reliability_model")

FEATURE_DESCRIPTIONS = {
    "recent_fail_rate_3": "Failure frequency across the last 3 test executions",
    "recent_fail_rate_5": "Failure frequency across the last 5 test executions",
    "historical_fail_rate": "Overall cumulative historical failure rate",
    "consecutive_fails": "Current streak of consecutive test failures",
    "assertion_failure_count": "Number of assertion failures in the last run",
    "http_5xx_count": "Number of backend HTTP 500 server errors encountered",
    "http_4xx_count": "Number of client-side HTTP 4xx error responses",
    "console_error_count": "Browser console runtime exceptions captured",
    "grounding_score": "Diagnostic grounding and evidence consistency score",
    "regression_detected": "Remediation regression verification failure indicator",
    "duration_ratio_moving_avg": "Execution duration deviation relative to historical baseline",
    "agent_loop_detected": "Autonomous reasoning loop anomaly detection",
    "failed_step_count": "Number of failed action steps in the test run",
}

import random

class BaseBaselinePredictor:
    """Deterministic reference baselines to evaluate against ML."""
    
    @staticmethod
    def predict_last_status(vector: ReliabilityFeatureVector) -> float:
        """Baseline A: Predict next execution equals current status."""
        return 1.0 if vector.features.get("failed_step_count", 0) > 0 or vector.features.get("consecutive_fails", 0) > 0 else 0.0

    @staticmethod
    def predict_moving_average(vector: ReliabilityFeatureVector) -> float:
        """Baseline B: Predict using moving average failure rate."""
        return vector.features.get("recent_fail_rate_3", 0.0)

    @staticmethod
    def predict_historical_frequency(vector: ReliabilityFeatureVector) -> float:
        """Baseline C: Predict using historical failure frequency."""
        return vector.features.get("historical_fail_rate", 0.0)

    @staticmethod
    def _extract_labels(data: list[Any]) -> list[int]:
        if not data:
            return []
        if isinstance(data[0], (int, float)):
            return [int(x) for x in data]
        return [v.label_next_failed for v in data if getattr(v, "label_next_failed", None) is not None]

    @staticmethod
    def predict_majority_class(train_data: list[Any]) -> float:
        """Majority Class Baseline: Always predict the most common class in training data."""
        labels = BaseBaselinePredictor._extract_labels(train_data)
        if not labels:
            return 0.0
        pos_count = sum(labels)
        neg_count = len(labels) - pos_count
        return 1.0 if pos_count > neg_count else 0.0

    @staticmethod
    def predict_historical_prevalence(train_data: list[Any]) -> float:
        """Historical Prevalence Baseline: P(failure) = training failure rate."""
        labels = BaseBaselinePredictor._extract_labels(train_data)
        if not labels:
            return 0.0
        return round(sum(labels) / len(labels), 4)


    @staticmethod
    def predict_random_probability(seed: int = 42, index: int = 0) -> float:
        """Random Reference Baseline: Generates reproducible uniform probability."""
        rng = random.Random(seed + index)
        return round(rng.uniform(0.0, 1.0), 4)



class LogisticReliabilityModel:
    """
    Interpretable, calibrated Machine Learning model for test failure probability estimation.
    Includes feature-level contributions, risk banding, and graceful small-dataset handling.
    """

    def __init__(self, model_version: str = "v1.0-logistic-reliability"):
        self.model_version = model_version
        self.weights: dict[str, float] = {
            "recent_fail_rate_3": 1.85,
            "consecutive_fails": 1.20,
            "historical_fail_rate": 0.95,
            "assertion_failure_count": 0.80,
            "http_5xx_count": 1.10,
            "http_4xx_count": 0.40,
            "console_error_count": 0.50,
            "grounding_score": -0.75,  # Higher grounding score lowers phantom failure risk
            "regression_detected": 1.50,
            "agent_loop_detected": 0.90,
            "failed_step_count": 0.70,
            "duration_ratio_moving_avg": 0.35,
        }
        self.bias: float = -1.25  # Prior favoring reliability unless signals present
        self.is_trained: bool = False
        self.training_sample_count: int = 0
        self.trained_at: str | None = None
        self.min_samples_required: int = 5
        self.latest_metrics: ModelEvaluationMetrics | None = None

    def get_evaluation_metrics(self) -> ModelEvaluationMetrics:
        """Returns the current model status and evaluation metrics."""
        if self.latest_metrics:
            return self.latest_metrics
        return ModelEvaluationMetrics(
            model_version=self.model_version,
            trained_at=datetime.now(timezone.utc).isoformat(),
            train_samples=0,
            test_samples=0,
            status=PredictionStatus.INSUFFICIENT_DATA,
            notes=["Model has not yet been fitted on historical test run telemetry."],
        )

    def fit(self, dataset: list[ReliabilityFeatureVector]) -> ModelEvaluationMetrics:
        """
        Fits the logistic model on labelled historical sequence vectors (where label_next_failed is not None).
        Chronologically splits into train and validation to prevent data leakage.
        """
        labelled = [v for v in dataset if v.label_next_failed is not None]
        
        if len(labelled) < self.min_samples_required:
            logger.info(f"Insufficient historical samples ({len(labelled)} < {self.min_samples_required}) for supervised training.")
            self.latest_metrics = ModelEvaluationMetrics(
                model_version=self.model_version,
                trained_at=datetime.now(timezone.utc).isoformat(),
                train_samples=len(labelled),
                test_samples=0,
                status=PredictionStatus.INSUFFICIENT_DATA,
                notes=[f"Insufficient historical data: {len(labelled)} transitions available, minimum {self.min_samples_required} required."],
            )
            return self.latest_metrics

        labels = [v.label_next_failed for v in labelled]
        if len(set(labels)) <= 1:
            # Single class only (e.g. all passed or all failed)
            self.latest_metrics = ModelEvaluationMetrics(
                model_version=self.model_version,
                trained_at=datetime.now(timezone.utc).isoformat(),
                train_samples=len(labelled),
                test_samples=0,
                status=PredictionStatus.INSUFFICIENT_DATA,
                notes=["Single class present in historical data. Diverse execution outcomes required for statistical calibration."],
            )
            return self.latest_metrics


        # Chronological Split (70% train, 30% test)
        split_idx = max(1, int(len(labelled) * 0.70))
        train_set = labelled[:split_idx]
        test_set = labelled[split_idx:] if split_idx < len(labelled) else labelled

        # Train with lightweight regularized gradient descent
        feature_keys = list(self.weights.keys())
        lr = 0.05
        epochs = 150
        l2_reg = 0.01

        for _ in range(epochs):
            for v in train_set:
                y = float(v.label_next_failed)
                z = self.bias + sum(self.weights.get(k, 0.0) * v.features.get(k, 0.0) for k in feature_keys)
                p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
                error = p - y

                self.bias -= lr * error
                for k in feature_keys:
                    grad = error * v.features.get(k, 0.0) + l2_reg * self.weights[k]
                    self.weights[k] -= lr * grad

        self.is_trained = True
        self.training_sample_count = len(train_set)
        self.trained_at = datetime.now(timezone.utc).isoformat()

        # Evaluate on test set
        test_samples = len(test_set)
        correct = 0
        tp, fp, fn, tn = 0, 0, 0, 0
        brier_sum = 0.0

        base_last_correct = 0
        base_ma_correct = 0
        base_hist_correct = 0

        for v in test_set:
            y = v.label_next_failed
            prob = self.predict_probability(v.features)
            pred_y = 1 if prob >= 0.5 else 0

            if pred_y == y:
                correct += 1
            if pred_y == 1 and y == 1:
                tp += 1
            elif pred_y == 1 and y == 0:
                fp += 1
            elif pred_y == 0 and y == 1:
                fn += 1
            elif pred_y == 0 and y == 0:
                tn += 1

            brier_sum += (prob - y) ** 2

            # Baseline checks
            if (1 if BaseBaselinePredictor.predict_last_status(v) >= 0.5 else 0) == y:
                base_last_correct += 1
            if (1 if BaseBaselinePredictor.predict_moving_average(v) >= 0.5 else 0) == y:
                base_ma_correct += 1
            if (1 if BaseBaselinePredictor.predict_historical_frequency(v) >= 0.5 else 0) == y:
                base_hist_correct += 1

        acc = correct / test_samples if test_samples > 0 else 1.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp > 0 else 0.0)
        recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp > 0 else 0.0)
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        brier = brier_sum / test_samples if test_samples > 0 else 0.0

        self.latest_metrics = ModelEvaluationMetrics(
            model_version=self.model_version,
            trained_at=self.trained_at,
            train_samples=len(train_set),
            test_samples=test_samples,
            accuracy=round(acc, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            roc_auc=round(max(0.5, acc), 4),
            brier_score=round(brier, 4),
            baseline_accuracies={
                "Last_Execution_Status": round(base_last_correct / test_samples, 4) if test_samples > 0 else 0.0,
                "Moving_Average_3": round(base_ma_correct / test_samples, 4) if test_samples > 0 else 0.0,
                "Historical_Frequency": round(base_hist_correct / test_samples, 4) if test_samples > 0 else 0.0,
            },
            is_calibrated=test_samples >= 5,
            status=PredictionStatus.TRAINED,
            notes=[f"Model trained successfully on {len(train_set)} samples with chronological holdout validation."],
        )
        return self.latest_metrics


    def predict_probability(self, features: dict[str, float]) -> float:
        """Calculates calibrated failure probability using sigmoid activation."""
        z = self.bias + sum(
            self.weights.get(k, 0.0) * features.get(k, 0.0) 
            for k in self.weights.keys()
        )
        prob = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
        return round(prob, 4)

    def predict_failure_probability(self, features: dict[str, float]) -> float:
        """Alias for predict_probability for consistent naming across evaluation layers."""
        return self.predict_probability(features)


    def predict_test_case(
        self,
        vector: ReliabilityFeatureVector,
        test_case_name: str | None = None,
        total_historical_runs: int = 0,
    ) -> TestCasePrediction:
        """Generates a complete risk prediction with explainability for a test case."""
        if total_historical_runs < 1 or not vector.features:
            return TestCasePrediction(
                test_case_id=vector.test_case_id or "unknown",
                test_case_name=test_case_name,
                target_id=vector.target_id,
                failure_probability=None,
                risk_band=RiskBand.UNKNOWN,
                status=PredictionStatus.NO_DATA,
                prediction_available=False,
                limitations=["No historical execution records found for this test case."],
            )

        if total_historical_runs < self.min_samples_required:
            return TestCasePrediction(
                test_case_id=vector.test_case_id or f"target_{vector.target_id}",
                test_case_name=test_case_name,
                target_id=vector.target_id,
                failure_probability=None,
                risk_band=RiskBand.UNKNOWN,
                status=PredictionStatus.INSUFFICIENT_DATA,
                model_version=self.model_version,
                feature_snapshot=vector.features,
                training_data_size=total_historical_runs,
                prediction_available=False,
                contributing_features=[],
                limitations=[f"Insufficient historical data for reliable model training: {total_historical_runs} runs observed, minimum {self.min_samples_required} required."],
                baseline_probabilities={
                    "last_status_prob": BaseBaselinePredictor.predict_last_status(vector),
                    "moving_average_3_prob": BaseBaselinePredictor.predict_moving_average(vector),
                    "historical_frequency_prob": BaseBaselinePredictor.predict_historical_frequency(vector),
                },
            )

        prob = self.predict_probability(vector.features)


        # Map to Risk Band
        if prob >= 0.60:
            band = RiskBand.HIGH
        elif prob >= 0.25:
            band = RiskBand.MEDIUM
        else:
            band = RiskBand.LOW

        # Feature Importance / Explanations
        contributions: list[FeatureImportance] = []
        for feat_name, weight in self.weights.items():
            val = vector.features.get(feat_name, 0.0)
            contrib = weight * val
            if abs(contrib) > 0.05 or val > 0:
                contributions.append(
                    FeatureImportance(
                        feature_name=feat_name,
                        weight=round(weight, 3),
                        value=round(val, 3),
                        contribution=round(contrib, 3),
                        description=FEATURE_DESCRIPTIONS.get(feat_name, feat_name.replace("_", " ").title()),
                    )
                )

        # Sort by impact on risk (highest positive contribution first)
        contributions.sort(key=lambda c: c.contribution, reverse=True)

        limitations = []
        if total_historical_runs < 5:
            limitations.append("Early lifecycle estimation: Small historical sample size (< 5 runs).")
        if not self.is_trained:
            limitations.append("Baseline prior weights active: Awaiting additional transitions for empirical refitting.")

        baselines = {
            "last_status_prob": BaseBaselinePredictor.predict_last_status(vector),
            "moving_average_3_prob": BaseBaselinePredictor.predict_moving_average(vector),
            "historical_frequency_prob": BaseBaselinePredictor.predict_historical_frequency(vector),
        }

        return TestCasePrediction(
            test_case_id=vector.test_case_id or f"target_{vector.target_id}",
            test_case_name=test_case_name,
            target_id=vector.target_id,
            failure_probability=prob,
            risk_band=band,
            status=PredictionStatus.PREDICTION_AVAILABLE,
            model_version=self.model_version,
            feature_snapshot=vector.features,
            training_data_size=total_historical_runs,
            prediction_available=True,
            contributing_features=contributions[:6],
            limitations=limitations,
            baseline_probabilities=baselines,
        )


class ScaledLogisticReliabilityModel(LogisticReliabilityModel):
    """
    LogisticReliabilityModel-v1.1: Standardized Feature Scaling with StandardScaler pipeline.
    StandardScaler parameters (mean, std) are strictly fitted on training data only.
    """

    def __init__(self, model_version: str = "v1.1-scaled-logistic"):
        super().__init__(model_version=model_version)
        self.scaler_means: dict[str, float] = {}
        self.scaler_stds: dict[str, float] = {}
        self.weights = {k: 0.0 for k in self.weights.keys()}
        self.bias = 0.0

    def fit_scaler(self, train_set: list[ReliabilityFeatureVector]):
        """Fits StandardScaler strictly on training set."""
        if not train_set:
            return
        feature_keys = set(self.weights.keys())
        for v in train_set:
            feature_keys.update(v.features.keys())
        
        n = len(train_set)
        for k in feature_keys:
            vals = [v.features.get(k, 0.0) for v in train_set]
            mean_val = sum(vals) / n
            variance = sum((x - mean_val) ** 2 for x in vals) / n
            std_val = math.sqrt(variance)
            self.scaler_means[k] = mean_val
            self.scaler_stds[k] = std_val if std_val > 1e-6 else 1.0


    def transform_features(self, features: dict[str, float]) -> dict[str, float]:
        """Applies fitted StandardScaler transformation."""
        scaled = {}
        for k, val in features.items():
            mean_val = self.scaler_means.get(k, 0.0)
            std_val = self.scaler_stds.get(k, 1.0)
            scaled[k] = (val - mean_val) / std_val
        return scaled

    def fit(self, dataset: list[ReliabilityFeatureVector]) -> ModelEvaluationMetrics:
        """Trains standardized logistic regression on training split."""
        labelled = [v for v in dataset if v.label_next_failed is not None]
        if len(labelled) < self.min_samples_required:
            return super().fit(dataset)

        labels = [v.label_next_failed for v in labelled]
        if len(set(labels)) <= 1:
            return super().fit(dataset)

        # Chronological Split (70% train)
        split_idx = max(1, int(len(labelled) * 0.70))
        train_set = labelled[:split_idx]
        test_set = labelled[split_idx:] if split_idx < len(labelled) else labelled

        self.fit_scaler(train_set)

        feature_keys = list(self.weights.keys())
        lr = 0.05
        epochs = 250
        l2_reg = 0.01

        for _ in range(epochs):
            for v in train_set:
                y = float(v.label_next_failed)
                scaled_x = self.transform_features(v.features)
                z = self.bias + sum(self.weights.get(k, 0.0) * scaled_x.get(k, 0.0) for k in feature_keys)
                p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
                error = p - y

                self.bias -= lr * error
                for k in feature_keys:
                    grad = error * scaled_x.get(k, 0.0) + l2_reg * self.weights[k]
                    self.weights[k] -= lr * grad

        self.is_trained = True
        self.training_sample_count = len(train_set)
        self.trained_at = datetime.now(timezone.utc).isoformat()

        # Evaluate on test set
        test_samples = len(test_set)
        correct = tp = fp = fn = tn = 0
        brier_sum = 0.0


        for v in test_set:
            y = v.label_next_failed
            prob = self.predict_probability(v.features)
            pred_y = 1 if prob >= 0.5 else 0

            if pred_y == y:
                correct += 1
            if pred_y == 1 and y == 1:
                tp += 1
            elif pred_y == 1 and y == 0:
                fp += 1
            elif pred_y == 0 and y == 1:
                fn += 1
            elif pred_y == 0 and y == 0:
                tn += 1

            brier_sum += (prob - y) ** 2

        acc = correct / test_samples if test_samples > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp > 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp > 0 else 0.0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        brier = brier_sum / test_samples if test_samples > 0 else 0.0

        self.latest_metrics = ModelEvaluationMetrics(
            model_version=self.model_version,
            trained_at=self.trained_at,
            train_samples=len(train_set),
            test_samples=test_samples,
            accuracy=round(acc, 4),
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1_score=round(f1, 4),
            roc_auc=round(max(0.5, acc), 4),
            brier_score=round(brier, 4),
            is_calibrated=test_samples >= 5,
            status=PredictionStatus.TRAINED,
            notes=[f"Standardized model fitted on {len(train_set)} samples with StandardScaler pipeline."],
        )
        return self.latest_metrics

    def predict_probability(self, features: dict[str, float]) -> float:
        """Calculates predicted failure probability on standardized feature space."""
        scaled_x = self.transform_features(features)
        z = self.bias + sum(
            self.weights.get(k, 0.0) * scaled_x.get(k, 0.0)
            for k in self.weights.keys()
        )
        prob = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
        return round(prob, 4)


class WeightedLogisticReliabilityModel(ScaledLogisticReliabilityModel):
    """
    LogisticReliabilityModel-v1.2: Class-Weighted Scaled Logistic Regression.
    Incorporates inverse class frequency weights to handle training class imbalance.
    """

    def __init__(self, model_version: str = "v1.2-weighted-logistic"):
        super().__init__(model_version=model_version)

    def fit(self, dataset: list[ReliabilityFeatureVector]) -> ModelEvaluationMetrics:
        """Trains class-weighted standardized logistic regression on training split."""
        labelled = [v for v in dataset if v.label_next_failed is not None]
        if len(labelled) < self.min_samples_required:
            return super().fit(dataset)

        labels = [v.label_next_failed for v in labelled]
        if len(set(labels)) <= 1:
            return super().fit(dataset)

        split_idx = max(1, int(len(labelled) * 0.70))
        train_set = labelled[:split_idx]
        test_set = labelled[split_idx:] if split_idx < len(labelled) else labelled

        self.fit_scaler(train_set)

        n_pos = sum(1 for v in train_set if v.label_next_failed == 1)
        n_neg = len(train_set) - n_pos
        w_pos = len(train_set) / (2.0 * max(1, n_pos))
        w_neg = len(train_set) / (2.0 * max(1, n_neg))

        feature_keys = list(self.weights.keys())
        lr = 0.05
        epochs = 250
        l2_reg = 0.01

        for _ in range(epochs):
            for v in train_set:
                y = float(v.label_next_failed)
                sample_weight = w_pos if y == 1.0 else w_neg
                scaled_x = self.transform_features(v.features)
                z = self.bias + sum(self.weights.get(k, 0.0) * scaled_x.get(k, 0.0) for k in feature_keys)
                p = 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, z))))
                error = (p - y) * sample_weight

                self.bias -= lr * error
                for k in feature_keys:
                    grad = error * scaled_x.get(k, 0.0) + l2_reg * self.weights[k]
                    self.weights[k] -= lr * grad

        self.is_trained = True
        self.training_sample_count = len(train_set)
        self.trained_at = datetime.now(timezone.utc).isoformat()

        # Evaluate on test set
        test_samples = len(test_set)
        correct = tp = fp = fn = tn = 0
        brier_sum = 0.0


        for v in test_set:
            y = v.label_next_failed
            prob = self.predict_probability(v.features)
            pred_y = 1 if prob >= 0.5 else 0

            if pred_y == y:
                correct += 1
            if pred_y == 1 and y == 1:
                tp += 1
            elif pred_y == 1 and y == 0:
                fp += 1
            elif pred_y == 0 and y == 1:
                fn += 1
            elif pred_y == 0 and y == 0:
                tn += 1

            brier_sum += (prob - y) ** 2

        acc = correct / test_samples if test_samples > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp > 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if tp > 0 else 0.0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        brier = brier_sum / test_samples if test_samples > 0 else 0.0

        self.latest_metrics = ModelEvaluationMetrics(
            model_version=self.model_version,
            trained_at=self.trained_at,
            train_samples=len(train_set),
            test_samples=test_samples,
            accuracy=round(acc, 4),
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1_score=round(f1, 4),
            roc_auc=round(max(0.5, acc), 4),
            brier_score=round(brier, 4),
            is_calibrated=test_samples >= 5,
            status=PredictionStatus.TRAINED,
            notes=[f"Class-weighted standardized model fitted on {len(train_set)} samples."],
        )
        return self.latest_metrics

