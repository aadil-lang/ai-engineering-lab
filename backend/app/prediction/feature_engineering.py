import logging
from typing import Any
from datetime import datetime

from backend.app.models.test_run import TestRun
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.diagnosis import EngineeringDiagnosis
from backend.app.models.remediation import RemediationTask
from backend.app.models.enums import (
    RunStatus,
    RunnerType,
    FailureCategory,
    GroundingStatus,
    RemediationStatus,
    ExecutionSource,
    CampaignType,
)
from backend.app.models.reliability import ReliabilityRecord, ReliabilityFeatureVector

logger = logging.getLogger("ai_qa_platform.feature_engineering")

class ReliabilityFeatureExtractor:
    """
    Extracts deterministic reliability features from historical QA telemetry
    without synthetic fabrication or temporal data leakage.
    """

    @classmethod
    def classify_execution_source(
        cls,
        run: TestRun,
        test_case_id: str | None = None,
        target_id: str | None = None,
    ) -> ExecutionSource:
        """
        Explicitly establishes execution provenance from actual run and runner configuration.
        Never infers provenance from target names, URLs, test-case names, or heuristics.
        """
        # 1. Honor explicit persisted execution_source if present and known
        if hasattr(run, "execution_source") and run.execution_source:
            if isinstance(run.execution_source, ExecutionSource) and run.execution_source != ExecutionSource.UNKNOWN:
                return run.execution_source
            elif isinstance(run.execution_source, str) and run.execution_source != "UNKNOWN":
                try:
                    return ExecutionSource(run.execution_source)
                except ValueError:
                    pass

        # 2. Derive strictly from the actual runner execution configuration
        runner = run.runner_type.value if hasattr(run.runner_type, "value") else str(run.runner_type)
        if runner in (RunnerType.PLAYWRIGHT.value, "PLAYWRIGHT"):
            return ExecutionSource.REAL_PLAYWRIGHT
        elif runner in (RunnerType.AI_AGENT.value, "AI_AGENT"):
            return ExecutionSource.REAL_AI_AGENT
        elif runner in (RunnerType.MOCK.value, "MOCK"):
            return ExecutionSource.SYNTHETIC_MOCK

        # 3. If provenance cannot be established, use UNKNOWN
        return ExecutionSource.UNKNOWN


    @classmethod
    def extract_record_from_run(
        cls,
        run: TestRun,
        evidence_items: list[Evidence],
        failures: list[Failure],
        diagnosis: EngineeringDiagnosis | None = None,
        remediation_task: RemediationTask | None = None,
    ) -> ReliabilityRecord:
        """Derives a structured ReliabilityRecord from raw run telemetry."""
        is_failed = 1 if run.status in (RunStatus.FAILED, RunStatus.ERROR) else 0

        # Step counts
        step_count = len(run.actions)
        failed_step_count = sum(1 for a in run.actions if a.status.value == "FAILED")

        # Telemetry counts from Evidence
        console_error_count = 0
        network_error_count = 0
        http_4xx_count = 0
        http_5xx_count = 0

        for evi in evidence_items:
            t = evi.evidence_type.value if hasattr(evi.evidence_type, "value") else str(evi.evidence_type)
            if t == "CONSOLE_LOG":
                events = evi.payload.get("events", []) if isinstance(evi.payload, dict) else []
                for ev in events:
                    if ev.get("type", "").lower() in ("error", "pageerror") or "uncaught" in ev.get("text", "").lower():
                        console_error_count += 1
            elif t == "NETWORK_HAR":
                events = evi.payload.get("events_sample", []) if isinstance(evi.payload, dict) else []
                if not events and isinstance(evi.payload, list):
                    events = evi.payload
                for ev in events:
                    if ev.get("event") == "response":
                        sc = ev.get("status", 200)
                        if sc >= 500:
                            http_5xx_count += 1
                            network_error_count += 1
                        elif sc >= 400:
                            http_4xx_count += 1
                            network_error_count += 1

        # Failure categories
        assertion_failure_count = sum(
            1 for f in failures 
            if f.category in (FailureCategory.ASSERTION_FAILURE, FailureCategory.ASSERTION_FAILED)
            or "assert" in f.message.lower()
        )
        navigation_failure_count = sum(
            1 for f in failures 
            if f.category == FailureCategory.NAVIGATION_TIMEOUT 
            or "navigation" in f.message.lower()
        )
        browser_error_count = sum(
            1 for f in failures 
            if f.category == FailureCategory.BROWSER_ERROR
        )
        agent_loop_detected = any(
            f.category == FailureCategory.AGENT_LOOP_DETECTED for f in failures
        ) or any("loop" in (a.thought or "").lower() for a in run.actions)

        # Diagnosis Grounding metrics
        grounding_score = diagnosis.grounding_score if diagnosis else 1.0
        unsupported_count = 0
        contradicted_count = 0
        if diagnosis and diagnosis.claims:
            for c in diagnosis.claims:
                if c.grounding_status == GroundingStatus.UNSUPPORTED:
                    unsupported_count += 1
                elif c.grounding_status == GroundingStatus.CONTRADICTED:
                    contradicted_count += 1

        # Remediation metrics
        remediation_attempts = len(remediation_task.attempts) if remediation_task else 0
        remediation_status = remediation_task.status.value if (remediation_task and hasattr(remediation_task.status, 'value')) else (remediation_task.status if remediation_task else None)
        regression_detected = any(v.regression_detected for v in remediation_task.verifications) if remediation_task else False

        exec_source = cls.classify_execution_source(
            run=run,
            test_case_id=run.test_case_id,
            target_id=run.application_id,
        )

        # Resolve application metadata
        target_id = run.application_id
        app_id = getattr(run, "application_id", target_id)
        app_type = getattr(run, "application_type", None)
        if target_id == "real_eda_local":
            app_id = "app_eda"
            app_type = "engineering_workflow"
        elif target_id == "real_inventory_local":
            app_id = "app_inventory"
            app_type = "crud_business"
        elif target_id == "real_booking_local":
            app_id = "app_booking"
            app_type = "stateful_workflow"
        elif "demo_shop" in str(target_id):
            app_id = "app_demo_shop"
            app_type = "demo_shop"

        return ReliabilityRecord(
            run_id=run.run_id,
            target_id=target_id,
            application_id=app_id,
            application_type=app_type,
            campaign_id=run.campaign_id,
            campaign_type=getattr(run, "campaign_type", None),
            test_case_id=run.test_case_id,
            timestamp=run.started_at,
            runner_type=run.runner_type.value if hasattr(run.runner_type, "value") else str(run.runner_type),
            run_status=run.status.value if hasattr(run.status, "value") else str(run.status),
            execution_source=exec_source,
            duration_ms=run.duration_ms or 0,
            step_count=step_count,
            failed_step_count=failed_step_count,
            assertion_failure_count=assertion_failure_count,
            console_error_count=console_error_count,
            network_error_count=network_error_count,
            http_4xx_count=http_4xx_count,
            http_5xx_count=http_5xx_count,
            navigation_failure_count=navigation_failure_count,
            browser_error_count=browser_error_count,
            agent_loop_detected=agent_loop_detected,
            grounding_score=grounding_score,
            unsupported_claim_count=unsupported_count,
            contradicted_claim_count=contradicted_count,
            remediation_attempts=remediation_attempts,
            remediation_status=remediation_status,
            regression_detected=regression_detected,
            failure_label=is_failed,
        )


    @classmethod
    def build_temporal_dataset(
        cls,
        records: list[ReliabilityRecord],
        enforce_stream_isolation: bool = True,
    ) -> list[ReliabilityFeatureVector]:
        """
        Constructs a temporal sequence dataset where features at execution t
        strictly predict failure outcome at t+1.
        Prevents all future leakage.

        When enforce_stream_isolation is True, sequences are partitioned by logical
        prediction stream (test_case_id/target_id AND execution_source), ensuring
        that feature t and target t+1 belong to the same execution stream and preventing
        cross-population contamination.
        """
        # Sort chronologically by timestamp, stably breaking ties by run_id
        sorted_records = sorted(records, key=lambda r: (r.timestamp, r.run_id))
        
        # Group by logical prediction stream
        sequences: dict[Any, list[ReliabilityRecord]] = {}
        for r in sorted_records:
            base_key = r.test_case_id or f"target_{r.target_id}"
            if enforce_stream_isolation and r.execution_source not in (ExecutionSource.UNKNOWN, None):
                key = (base_key, r.execution_source)
            else:
                key = base_key
            sequences.setdefault(key, []).append(r)

        feature_vectors: list[ReliabilityFeatureVector] = []

        for key, seq in sequences.items():
            for i, current in enumerate(seq):
                # Historical sequence up to i (inclusive) - STRICTLY PAST
                past = seq[:i + 1]
                
                # Compute historical rolling features
                recent_3 = past[-3:]
                recent_5 = past[-5:]
                
                recent_fail_rate_3 = sum(p.failure_label for p in recent_3) / len(recent_3)
                recent_fail_rate_5 = sum(p.failure_label for p in recent_5) / len(recent_5)
                cumulative_fail_rate = sum(p.failure_label for p in past) / len(past)
                
                # Consecutive failures ending at current
                consecutive_fails = 0
                for p in reversed(past):
                    if p.failure_label == 1:
                        consecutive_fails += 1
                    else:
                        break

                # Duration ratio vs moving average
                durations = [p.duration_ms for p in past]
                avg_duration = sum(durations) / len(durations) if durations else 1.0
                duration_ratio = (current.duration_ms / avg_duration) if avg_duration > 0 else 1.0

                features: dict[str, float] = {
                    "duration_ms": float(current.duration_ms),
                    "step_count": float(current.step_count),
                    "failed_step_count": float(current.failed_step_count),
                    "assertion_failure_count": float(current.assertion_failure_count),
                    "console_error_count": float(current.console_error_count),
                    "network_error_count": float(current.network_error_count),
                    "http_5xx_count": float(current.http_5xx_count),
                    "http_4xx_count": float(current.http_4xx_count),
                    "navigation_failure_count": float(current.navigation_failure_count),
                    "browser_error_count": float(current.browser_error_count),
                    "agent_loop_detected": 1.0 if current.agent_loop_detected else 0.0,
                    "grounding_score": float(current.grounding_score),
                    "unsupported_claim_count": float(current.unsupported_claim_count),
                    "contradicted_claim_count": float(current.contradicted_claim_count),
                    "remediation_attempts": float(current.remediation_attempts),
                    "regression_detected": 1.0 if current.regression_detected else 0.0,
                    "is_runner_ai": 1.0 if current.runner_type == "AI_AGENT" else 0.0,
                    "is_runner_playwright": 1.0 if current.runner_type == "PLAYWRIGHT" else 0.0,
                    "recent_fail_rate_3": float(recent_fail_rate_3),
                    "recent_fail_rate_5": float(recent_fail_rate_5),
                    "historical_fail_rate": float(cumulative_fail_rate),
                    "consecutive_fails": float(consecutive_fails),
                    "duration_ratio_moving_avg": float(duration_ratio),
                }

                # Next execution label (t + 1)
                if i + 1 < len(seq):
                    next_record = seq[i + 1]
                    # Verify non-negotiable integrity constraints
                    if next_record.run_id == current.run_id:
                        raise ValueError(f"Integrity violation: Run {current.run_id} cannot have itself as target")
                    next_label = next_record.failure_label
                    target_run_id = next_record.run_id
                    target_exec_source = next_record.execution_source
                    target_camp_type = next_record.campaign_type
                else:
                    next_label = None
                    target_run_id = None
                    target_exec_source = None
                    target_camp_type = None

                feature_vectors.append(
                    ReliabilityFeatureVector(
                        run_id=current.run_id,
                        test_case_id=current.test_case_id,
                        target_id=current.target_id,
                        application_id=current.application_id or current.target_id,
                        application_type=current.application_type,
                        campaign_id=current.campaign_id,
                        campaign_type=current.campaign_type,
                        timestamp=current.timestamp,
                        execution_source=current.execution_source,
                        features=features,
                        label_next_failed=next_label,
                        target_run_id=target_run_id,
                        target_execution_source=target_exec_source,
                        target_campaign_type=target_camp_type,
                    )
                )

        return feature_vectors


