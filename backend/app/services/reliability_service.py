import uuid
import logging
from typing import Any
from datetime import datetime, timezone
from collections import defaultdict

from backend.app.models.enums import (
    TrendStatus,
    RiskBand,
    PredictionStatus,
    RunStatus,
    RemediationStatus,
    DatasetStatus,
    PredictionEvaluationStatus,
    EvaluationSplitType,
    PopulationType,
    ExecutionSource,
)
from backend.app.models.reliability import (
    ReliabilityRecord,
    ReliabilitySummary,
    TargetReliability,
    TestCaseReliability,
    FailurePattern,
    TrendPoint,
    TrendAnalysis,
    TestCasePrediction,
    QAPrioritizationItem,
    ModelEvaluationMetrics,
    ReliabilityFeatureVector,
    DatasetAuditReport,
    DatasetProvenanceRecord,
    ContinuousScientificEvaluationReport,
    PredictionRecord,
    DatasetDiagnosticsReport,
    PopulationSeparationReport,
    WalkForwardEvaluationReport,
)

from backend.app.repositories.base import (
    RunRepositoryInterface,
    TargetRepositoryInterface,
    TestCaseRepositoryInterface,
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    DiagnosisRepositoryInterface,
    RemediationRepositoryInterface,
    PredictionRecordRepositoryInterface,
)
from backend.app.prediction.feature_engineering import ReliabilityFeatureExtractor
from backend.app.prediction.reliability_model import LogisticReliabilityModel
from backend.app.prediction.scientific_evaluator import ScientificEvaluator
from backend.app.prediction.dataset_diagnostics import DatasetDiagnosticsEngine
from backend.app.prediction.walk_forward_evaluator import (
    ProductionReliabilityDatasetAnalyzer,
    WalkForwardEvaluator,
)



logger = logging.getLogger("ai_qa_platform.reliability_service")

class ReliabilityService:
    """
    Service orchestrating historical QA telemetry extraction, trend analysis,
    grounded failure pattern analytics, and predictive failure risk modeling.
    """

    def __init__(
        self,
        run_repo: RunRepositoryInterface,
        target_repo: TargetRepositoryInterface,
        test_case_repo: TestCaseRepositoryInterface,
        evidence_repo: EvidenceRepositoryInterface,
        failure_repo: FailureRepositoryInterface,
        diagnosis_repo: DiagnosisRepositoryInterface,
        remediation_repo: RemediationRepositoryInterface,
        prediction_record_repo: PredictionRecordRepositoryInterface | None = None,
        model: LogisticReliabilityModel | None = None,
    ):
        self.run_repo = run_repo
        self.target_repo = target_repo
        self.test_case_repo = test_case_repo
        self.evidence_repo = evidence_repo
        self.failure_repo = failure_repo
        self.diagnosis_repo = diagnosis_repo
        self.remediation_repo = remediation_repo
        self.prediction_record_repo = prediction_record_repo or (
            run_repo if hasattr(run_repo, "save_prediction_record") else None
        )
        self.model = model or LogisticReliabilityModel()

    def _collect_all_records(self) -> list[ReliabilityRecord]:
        """Extracts structured reliability records for all historical runs in the database."""
        runs = self.run_repo.list_runs(limit=500)
        records: list[ReliabilityRecord] = []

        for run in runs:
            evidence = self.evidence_repo.get_evidence_by_run(run.run_id)
            failures = self.failure_repo.get_failures_by_run(run.run_id)
            diagnosis = self.diagnosis_repo.get_diagnosis_by_run(run.run_id)
            
            remed_tasks = self.remediation_repo.get_remediation_tasks_by_run(run.run_id)
            remediation_task = remed_tasks[0] if remed_tasks else None

            rec = ReliabilityFeatureExtractor.extract_record_from_run(
                run=run,
                evidence_items=evidence,
                failures=failures,
                diagnosis=diagnosis,
                remediation_task=remediation_task,
            )
            records.append(rec)

        return records

    def get_summary(self) -> ReliabilitySummary:
        """Calculates global reliability KPI metrics across all test executions."""
        records = self._collect_all_records()
        total_runs = len(records)
        targets = self.target_repo.list_targets()
        test_cases = self.test_case_repo.list_test_cases()

        if total_runs == 0:
            return ReliabilitySummary(
                total_runs=0,
                total_failures=0,
                failure_rate=0.0,
                successful_remediation_rate=0.0,
                regression_rate=0.0,
                avg_remediation_attempts=0.0,
                avg_execution_duration_ms=0.0,
                prediction_coverage_pct=0.0,
                active_targets_count=len(targets),
                active_test_cases_count=len(test_cases),
                overall_trend=TrendStatus.INSUFFICIENT_DATA,
            )

        total_failures = sum(r.failure_label for r in records)
        failure_rate = round(total_failures / total_runs, 4)

        # Remediation & Regression stats
        all_remed_tasks = self.remediation_repo.list_remediation_tasks(limit=500)
        resolved_count = sum(1 for t in all_remed_tasks if t.status in (RemediationStatus.RESOLVED, "RESOLVED"))
        remed_rate = round(resolved_count / len(all_remed_tasks), 4) if all_remed_tasks else 0.0

        all_verifications = [v for t in all_remed_tasks for v in t.verifications]
        regressions = sum(1 for v in all_verifications if v.regression_detected)
        reg_rate = round(regressions / len(all_verifications), 4) if all_verifications else 0.0

        all_attempts = [a for t in all_remed_tasks for a in t.attempts]
        avg_attempts = round(len(all_attempts) / len(all_remed_tasks), 2) if all_remed_tasks else 0.0

        avg_duration = round(sum(r.duration_ms for r in records) / total_runs, 1)

        # Trend analysis
        trend_analysis = self.get_trends(records=records)

        # Prediction coverage
        pred_items = self.get_test_case_predictions(records=records)
        available_preds = sum(1 for p in pred_items if p.prediction_available)
        coverage_pct = round((available_preds / len(pred_items)) * 100, 1) if pred_items else 0.0

        return ReliabilitySummary(
            total_runs=total_runs,
            total_failures=total_failures,
            failure_rate=failure_rate,
            successful_remediation_rate=remed_rate,
            regression_rate=reg_rate,
            avg_remediation_attempts=avg_attempts,
            avg_execution_duration_ms=avg_duration,
            prediction_coverage_pct=coverage_pct,
            active_targets_count=len(targets),
            active_test_cases_count=len(test_cases),
            overall_trend=trend_analysis.overall_trend,
        )

    def get_trends(self, records: list[ReliabilityRecord] | None = None) -> TrendAnalysis:
        """Analyzes historical failure rate changes and temporal direction."""
        if records is None:
            records = self._collect_all_records()

        if len(records) < 3:
            return TrendAnalysis(
                overall_trend=TrendStatus.INSUFFICIENT_DATA,
                historical_failure_rate=0.0,
                recent_failure_rate=0.0,
                data_points=[],
                trend_description="Insufficient execution history (minimum 3 runs required for trend calculation).",
            )

        sorted_records = sorted(records, key=lambda r: r.timestamp)
        hist_failures = sum(r.failure_label for r in sorted_records)
        hist_rate = round(hist_failures / len(sorted_records), 4)

        # Recent window: last 5 runs or 30% of history
        recent_window_size = max(3, int(len(sorted_records) * 0.35))
        recent_records = sorted_records[-recent_window_size:]
        recent_failures = sum(r.failure_label for r in recent_records)
        recent_rate = round(recent_failures / len(recent_records), 4)

        # Determine trend direction
        delta = recent_rate - hist_rate
        if delta <= -0.05:
            trend = TrendStatus.IMPROVING
            desc = f"Failure rate decreased from {int(hist_rate * 100)}% to {int(recent_rate * 100)}% over recent runs."
        elif delta >= 0.05:
            trend = TrendStatus.DEGRADING
            desc = f"Failure rate increased from {int(hist_rate * 100)}% to {int(recent_rate * 100)}% over recent runs."
        else:
            trend = TrendStatus.STABLE
            desc = f"Failure rate remains steady at ~{int(recent_rate * 100)}%."

        # Group data points by date / bucket
        buckets: dict[str, list[int]] = defaultdict(list)
        for r in sorted_records:
            date_key = r.timestamp[:10] if len(r.timestamp) >= 10 else "Recent"
            buckets[date_key].append(r.failure_label)

        data_points = [
            TrendPoint(
                time_bucket=k,
                total_runs=len(v),
                failed_runs=sum(v),
                failure_rate=round(sum(v) / len(v), 4),
            )
            for k, v in buckets.items()
        ]

        return TrendAnalysis(
            overall_trend=trend,
            historical_failure_rate=hist_rate,
            recent_failure_rate=recent_rate,
            data_points=data_points,
            trend_description=desc,
        )

    def get_target_reliability(self, target_id: str) -> TargetReliability:
        """Returns reliability analytics and grounded component attribution for a specific target."""
        target = self.target_repo.get_target(target_id)
        target_name = target.name if target else target_id

        records = [r for r in self._collect_all_records() if r.target_id == target_id]
        if not records:
            return TargetReliability(
                target_id=target_id,
                target_name=target_name,
                run_count=0,
                failure_count=0,
                failure_rate=0.0,
                recent_trend=TrendStatus.INSUFFICIENT_DATA,
                grounded_component_failures={},
            )

        run_count = len(records)
        fail_count = sum(r.failure_label for r in records)
        fail_rate = round(fail_count / run_count, 4)

        # Grounded component failure breakdown (only from verified diagnosis!)
        grounded_comp_failures: dict[str, int] = defaultdict(int)
        for r in records:
            if r.failure_label == 1:
                diag = self.diagnosis_repo.get_diagnosis_by_run(r.run_id)
                if diag and (diag.is_grounded or diag.grounded_suspected_component):
                    comp = diag.grounded_suspected_component or diag.suspected_component
                    grounded_comp_failures[comp] += 1

        # Trend for this target
        sorted_target_records = sorted(records, key=lambda r: r.timestamp)
        recent = sorted_target_records[-max(2, int(len(records) * 0.4)):]
        recent_rate = sum(r.failure_label for r in recent) / len(recent) if recent else fail_rate

        if len(records) < 3:
            trend = TrendStatus.INSUFFICIENT_DATA
        elif recent_rate < fail_rate - 0.05:
            trend = TrendStatus.IMPROVING
        elif recent_rate > fail_rate + 0.05:
            trend = TrendStatus.DEGRADING
        else:
            trend = TrendStatus.STABLE

        return TargetReliability(
            target_id=target_id,
            target_name=target_name,
            run_count=run_count,
            failure_count=fail_count,
            failure_rate=fail_rate,
            recent_trend=trend,
            grounded_component_failures=dict(grounded_comp_failures),
        )

    def list_targets_reliability(self) -> list[TargetReliability]:
        """Lists reliability analytics for all registered application targets."""
        targets = self.target_repo.list_targets()
        return [self.get_target_reliability(t.target_id) for t in targets]

    def get_test_case_reliability(self, test_case_id: str) -> TestCaseReliability:
        """Returns historical reliability metrics and risk prediction for a specific test case."""
        tc = self.test_case_repo.get_test_case(test_case_id)
        tc_name = tc.name if tc else test_case_id
        target_id = tc.target_id if tc else "unknown"

        records = [r for r in self._collect_all_records() if r.test_case_id == test_case_id]
        if not records:
            return TestCaseReliability(
                test_case_id=test_case_id,
                test_case_name=tc_name,
                target_id=target_id,
                execution_count=0,
                failure_count=0,
                failure_rate=0.0,
                recent_trend=TrendStatus.INSUFFICIENT_DATA,
                last_run_status=None,
                last_run_timestamp=None,
                prediction=None,
            )

        sorted_records = sorted(records, key=lambda r: r.timestamp)
        exec_count = len(sorted_records)
        fail_count = sum(r.failure_label for r in sorted_records)
        fail_rate = round(fail_count / exec_count, 4)

        last_rec = sorted_records[-1]

        # Trend calculation
        recent = sorted_records[-max(2, int(len(sorted_records) * 0.4)):]
        recent_rate = sum(r.failure_label for r in recent) / len(recent) if recent else fail_rate

        if len(sorted_records) < 3:
            trend = TrendStatus.INSUFFICIENT_DATA
        elif recent_rate < fail_rate - 0.05:
            trend = TrendStatus.IMPROVING
        elif recent_rate > fail_rate + 0.05:
            trend = TrendStatus.DEGRADING
        else:
            trend = TrendStatus.STABLE

        # Generate feature vector for latest state
        temporal_dataset = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        latest_vector = temporal_dataset[-1] if temporal_dataset else None

        prediction = None
        if latest_vector:
            prediction = self.model.predict_test_case(
                vector=latest_vector,
                test_case_name=tc_name,
                total_historical_runs=exec_count,
            )

        return TestCaseReliability(
            test_case_id=test_case_id,
            test_case_name=tc_name,
            target_id=target_id,
            execution_count=exec_count,
            failure_count=fail_count,
            failure_rate=fail_rate,
            recent_trend=trend,
            last_run_status=last_rec.run_status,
            last_run_timestamp=last_rec.timestamp,
            prediction=prediction,
        )

    def list_test_cases_reliability(self) -> list[TestCaseReliability]:
        """Lists reliability analytics and predictions for all registered test cases."""
        test_cases = self.test_case_repo.list_test_cases()
        return [self.get_test_case_reliability(tc.test_case_id) for tc in test_cases]

    def get_failure_patterns(self) -> list[FailurePattern]:
        """Aggregates failure categories with grounded component correlations."""
        records = self._collect_all_records()
        failed_records = [r for r in records if r.failure_label == 1]
        
        if not failed_records:
            return []

        category_counts: dict[str, int] = defaultdict(int)
        category_durations: dict[str, list[int]] = defaultdict(list)
        category_grounded_components: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for r in failed_records:
            failures = self.failure_repo.get_failures_by_run(r.run_id)
            diag = self.diagnosis_repo.get_diagnosis_by_run(r.run_id)
            
            cat = failures[0].category.value if failures else "UNKNOWN_ERROR"
            category_counts[cat] += 1
            category_durations[cat].append(r.duration_ms)

            if diag and (diag.is_grounded or diag.grounded_suspected_component):
                comp = diag.grounded_suspected_component or diag.suspected_component
                if comp:
                    category_grounded_components[cat][comp] += 1

        total_fails = len(failed_records)
        patterns: list[FailurePattern] = []

        for cat, cnt in category_counts.items():
            durations = category_durations[cat]
            avg_dur = round(sum(durations) / len(durations), 1) if durations else 0.0
            top_comps = sorted(
                category_grounded_components[cat].keys(),
                key=lambda c: category_grounded_components[cat][c],
                reverse=True,
            )[:8]

            patterns.append(
                FailurePattern(
                    category=cat,
                    count=cnt,
                    percentage=round((cnt / total_fails) * 100, 1),
                    avg_duration_ms=avg_dur,
                    top_grounded_components=top_comps,
                )
            )

        patterns.sort(key=lambda p: p.count, reverse=True)
        return patterns


    def _record_prediction_if_new(self, pred: TestCasePrediction, vec: ReliabilityFeatureVector) -> PredictionRecord | None:
        """Persists a pending prediction record for a test case if not already tracked."""
        if not self.prediction_record_repo or not pred.test_case_id:
            return None
        pending = self.prediction_record_repo.get_pending_predictions_for_test_case(pred.test_case_id)
        for p in pending:
            if p.feature_run_id == vec.run_id:
                return p
        
        prob = pred.failure_probability or 0.0
        pred_class = 1 if prob >= 0.5 else 0
        pred_rec = PredictionRecord(
            prediction_id=f"pred_{uuid.uuid4().hex[:10]}",
            test_case_id=pred.test_case_id,
            test_case_name=pred.test_case_name,
            feature_run_id=vec.run_id,
            predicted_failure_probability=prob,
            predicted_risk_band=pred.risk_band,
            prediction_class=pred_class,
            model_version=getattr(self.model, "model_version", "1.0.0"),
            feature_vector_version="v1.0",
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            target_run_id=None,
            actual_outcome=None,
            is_correct=None,
            evaluation_status=PredictionEvaluationStatus.PENDING,
            evaluated_at=None,
        )
        self.prediction_record_repo.save_prediction_record(pred_rec)
        return pred_rec

    def get_test_case_predictions(self, records: list[ReliabilityRecord] | None = None) -> list[TestCasePrediction]:
        """Calculates current failure risk predictions for all active test cases and targets."""
        if records is None:
            records = self._collect_all_records()

        temporal_dataset = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        if not temporal_dataset:
            return []

        # Find latest vector per test_case_id or target_id
        latest_vectors: dict[str, tuple[ReliabilityFeatureVector, int]] = {}
        for v in temporal_dataset:
            key = v.test_case_id or f"target_{v.target_id}"
            curr_count = latest_vectors.get(key, (None, 0))[1] + 1
            latest_vectors[key] = (v, curr_count)

        predictions: list[TestCasePrediction] = []
        for key, (vec, count) in latest_vectors.items():
            tc_name = None
            if vec.test_case_id:
                tc = self.test_case_repo.get_test_case(vec.test_case_id)
                if tc:
                    tc_name = tc.name

            pred = self.model.predict_test_case(
                vector=vec,
                test_case_name=tc_name,
                total_historical_runs=count,
            )
            predictions.append(pred)

            if self.prediction_record_repo and pred.test_case_id and pred.prediction_available:
                self._record_prediction_if_new(pred, vec)

        # Sort by failure probability descending
        predictions.sort(key=lambda p: (p.failure_probability or 0.0), reverse=True)
        return predictions

    def get_qa_prioritization(self) -> list[QAPrioritizationItem]:
        """
        Generates risk-aware QA test scheduling recommendations.
        Prioritizes high-risk, degrading, or regression-prone test paths for the next QA cycle.
        """
        predictions = self.get_test_case_predictions()
        test_case_reliabilities = self.list_test_cases_reliability()
        rel_map = {r.test_case_id: r for r in test_case_reliabilities}

        items: list[QAPrioritizationItem] = []
        rank = 1

        for pred in predictions:
            tc_rel = rel_map.get(pred.test_case_id)
            trend = tc_rel.recent_trend if tc_rel else TrendStatus.INSUFFICIENT_DATA
            
            # Formulate clear rationale
            reasons = []
            prob = pred.failure_probability or 0.0
            
            if pred.risk_band == RiskBand.HIGH:
                reasons.append(f"Elevated failure risk probability ({int(prob * 100)}%)")
            elif pred.risk_band == RiskBand.MEDIUM:
                reasons.append(f"Moderate failure risk probability ({int(prob * 100)}%)")
                
            if trend == TrendStatus.DEGRADING:
                reasons.append("Recent failure rate trend is degrading")
            elif tc_rel and tc_rel.failure_rate >= 0.5:
                reasons.append(f"High historical failure rate ({int(tc_rel.failure_rate * 100)}%)")

            if pred.feature_snapshot.get("regression_detected", 0) > 0:
                reasons.append("Recent remediation regression detected")
            if pred.feature_snapshot.get("consecutive_fails", 0) >= 2:
                reasons.append(f"Consecutive failure streak ({int(pred.feature_snapshot.get('consecutive_fails', 0))})")

            if not reasons:
                reasons.append("Standard regression baseline verification")

            items.append(
                QAPrioritizationItem(
                    priority_rank=rank,
                    test_case_id=pred.test_case_id,
                    test_case_name=pred.test_case_name or pred.test_case_id,
                    target_id=pred.target_id,
                    risk_band=pred.risk_band,
                    failure_probability=pred.failure_probability,
                    trend=trend,
                    reason=" | ".join(reasons),
                )
            )
            rank += 1

        return items

    def train_model(self) -> ModelEvaluationMetrics:
        """Trains the ML reliability model on historical execution sequences and returns evaluation metrics."""
        records = self._collect_all_records()
        temporal_dataset = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        return self.model.fit(temporal_dataset)

    # ==========================================
    # Slice 6.1: Scientific Validation & Continuous Tracking
    # ==========================================

    def get_dataset_audit(self) -> DatasetAuditReport:
        """Generates a formal statistical audit of all genuine historical QA executions."""
        records = self._collect_all_records()
        return ScientificEvaluator.audit_dataset(records)

    def get_provenance_records(self) -> list[DatasetProvenanceRecord]:
        """Generates traceable provenance records validating strict temporal sequencing without data leakage."""
        records = self._collect_all_records()
        return ScientificEvaluator.build_provenance_records(records)

    def list_prediction_records(self, test_case_id: str | None = None, limit: int = 100) -> list[PredictionRecord]:
        """Lists historical and active prediction tracking records."""
        if not self.prediction_record_repo:
            return []
        return self.prediction_record_repo.list_prediction_records(test_case_id=test_case_id, limit=limit)

    def record_prediction(
        self,
        test_case_id: str,
        test_case_name: str | None,
        feature_run_id: str,
        predicted_failure_probability: float,
        predicted_risk_band: RiskBand,
        prediction_class: int,
        model_version: str = "1.0.0",
        feature_vector_version: str = "v1.0",
    ) -> PredictionRecord:
        """Explicitly records a prediction for continuous outcome monitoring."""
        pred_rec = PredictionRecord(
            prediction_id=f"pred_{uuid.uuid4().hex[:10]}",
            test_case_id=test_case_id,
            test_case_name=test_case_name,
            feature_run_id=feature_run_id,
            predicted_failure_probability=predicted_failure_probability,
            predicted_risk_band=predicted_risk_band,
            prediction_class=prediction_class,
            model_version=model_version,
            feature_vector_version=feature_vector_version,
            prediction_timestamp=datetime.now(timezone.utc).isoformat(),
            target_run_id=None,
            actual_outcome=None,
            is_correct=None,
            evaluation_status=PredictionEvaluationStatus.PENDING,
            evaluated_at=None,
        )
        if self.prediction_record_repo:
            self.prediction_record_repo.save_prediction_record(pred_rec)
        return pred_rec

    def evaluate_pending_predictions_for_run(self, run: Any) -> list[PredictionRecord]:
        """
        Evaluates any pending predictions for the run's test case once this new run completes.
        Links feature run -> target run -> actual outcome.
        """
        if not self.prediction_record_repo or not getattr(run, "test_case_id", None):
            return []
        
        pending_list = self.prediction_record_repo.get_pending_predictions_for_test_case(run.test_case_id)
        if not pending_list:
            return []

        status_val = run.status.value if hasattr(run.status, "value") else str(run.status)
        is_failed = status_val in ("FAILED", "ERROR")
        actual_outcome = 1 if is_failed else 0
        now_iso = datetime.now(timezone.utc).isoformat()
        
        evaluated: list[PredictionRecord] = []
        for p in pending_list:
            if p.feature_run_id == run.run_id:
                continue
            p.target_run_id = run.run_id
            p.actual_outcome = actual_outcome
            p.is_correct = (p.prediction_class == actual_outcome)
            p.evaluation_status = PredictionEvaluationStatus.EVALUATED
            p.evaluated_at = now_iso
            self.prediction_record_repo.update_prediction_record(p)
            evaluated.append(p)
            
        return evaluated

    def get_scientific_evaluation(self) -> ContinuousScientificEvaluationReport:
        """
        Generates comprehensive scientific evaluation comparing logistic model with deterministic
        baselines A, B, C across chronological splits, with empirical calibration and continuous tracking.
        """
        records = self._collect_all_records()
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        prediction_records = self.list_prediction_records(limit=100)
        return ScientificEvaluator.generate_scientific_report(
            records=records,
            vectors=vectors,
            model=self.model,
            prediction_records=prediction_records,
        )

    def get_dataset_diagnostics(self) -> DatasetDiagnosticsReport:
        """
        Generates comprehensive dataset diagnostics and model failure analysis.
        Investigates distribution shifts, sequence autocorrelation, class imbalance,
        and benchmarks multiple model variants (v1.0, v1.1-scaled, v1.2-weighted).
        """
        records = self._collect_all_records()
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        return DatasetDiagnosticsEngine.generate_diagnostics_report(
            records=records,
            vectors=vectors,
            model=self.model,
        )

    def get_population_separation_report(
        self,
        min_train_size: int = 20,
        step_size: int = 5,
    ) -> PopulationSeparationReport:
        """
        Generates production-grade population separation and walk-forward cross-validation analysis.
        Separates real browser & AI agent executions from synthetic mock and demo shop harness runs.
        """
        records = self._collect_all_records()
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        return ProductionReliabilityDatasetAnalyzer.generate_population_separation_report(
            records=records,
            vectors=vectors,
            min_train_size=min_train_size,
            step_size=step_size,
        )

    def get_walk_forward_evaluation(
        self,
        population: PopulationType = PopulationType.ALL_HISTORICAL,
        min_train_size: int = 20,
        step_size: int = 5,
    ) -> WalkForwardEvaluationReport:
        """
        Conducts expanding-window walk-forward temporal cross-validation on a specific execution population.
        """
        records = self._collect_all_records()
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        return WalkForwardEvaluator.run_walk_forward_evaluation(
            vectors=vectors,
            population=population,
            min_train_size=min_train_size,
            step_size=step_size,
        )

    def get_cross_application_evaluation_report(self) -> Any:
        """
        Executes Slice 6.9 Cross-Application Reliability Evaluation & Generalization across
        Regime A (Within-App), Regime B (LOAO), and Regime C (Combined Temporal).
        """
        from backend.app.prediction.cross_app_evaluator import CrossAppEvaluator
        records = self._collect_all_records()
        vectors = ReliabilityFeatureExtractor.build_temporal_dataset(records)
        return CrossAppEvaluator.run_complete_evaluation(
            records=records,
            vectors=vectors,
        )




