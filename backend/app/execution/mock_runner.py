import asyncio
import time
from datetime import datetime, timezone
import uuid

from backend.app.execution.base_runner import BaseTestRunner
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_action import TestAction
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.metric import Metric
from backend.app.models.enums import (
    ActionType,
    ActionStatus,
    EvidenceType,
    RunStatus,
    FailureCategory,
    Severity,
    TestMode,
    ExecutionSource,
)
from backend.app.repositories.base import (
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    MetricRepositoryInterface,
    RunRepositoryInterface,
)

class MockTestRunner(BaseTestRunner):
    """
    Deterministic Mock Test Runner.
    Simulates real user interaction across 5 sequential actions:
    1. Navigate to application
    2. Locate element
    3. Click element
    4. Enter input
    5. Submit workflow

    Each step collects rich, structured telemetry and evidence.
    """
    def __init__(
        self,
        run_repo: RunRepositoryInterface,
        evidence_repo: EvidenceRepositoryInterface,
        failure_repo: FailureRepositoryInterface,
        metric_repo: MetricRepositoryInterface,
    ):
        self.run_repo = run_repo
        self.evidence_repo = evidence_repo
        self.failure_repo = failure_repo
        self.metric_repo = metric_repo

    async def execute(self, run: TestRun, target: ApplicationTarget, options: TestRunCreate) -> TestRun:
        start_time = time.time()
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(timezone.utc).isoformat()
        if not run.execution_source or run.execution_source == ExecutionSource.UNKNOWN:
            if options.execution_source and options.execution_source != ExecutionSource.UNKNOWN:
                run.execution_source = options.execution_source
            else:
                run.execution_source = ExecutionSource.SYNTHETIC_MOCK
        self.run_repo.update_run(run)

        delay_seconds = (options.action_delay_ms or 150) / 1000.0

        # Define 5 standard simulated steps
        steps_plan = [
            {
                "type": ActionType.NAVIGATE,
                "description": f"Navigate to target URL: {target.base_url}",
                "input": {"url": target.base_url, "timeout_ms": 5000, "headers": {"User-Agent": "ReliabilityAgent/1.0"}},
                "output": {"http_status": 200, "page_title": f"{target.name} - Portal", "load_time_ms": 142},
                "evidence_type": EvidenceType.DOM_SNAPSHOT,
                "evidence_title": "Initial DOM Tree & Layout Snapshot",
                "evidence_payload": {
                    "doctype": "html",
                    "title": target.name,
                    "url": target.base_url,
                    "nodes_count": 342,
                    "html_snippet": f"<!DOCTYPE html><html><head><title>{target.name}</title></head><body><header class='nav-bar'><div class='logo'>AutoShop</div></header><main><section id='checkout-form'><div class='cart-summary'>Items: 2</div></section></main></body></html>"
                },
                "metric_name": "page_load_time_ms",
                "metric_val": 142.0,
            },
            {
                "type": ActionType.LOCATE,
                "description": "Locate interactive checkout element: '#checkout-form input[name=\"promo_code\"]'",
                "input": {"selector": "#checkout-form input[name=\"promo_code\"]", "strategy": "css_selector", "visible": True},
                "output": {"found": True, "element_tag": "input", "bounds": {"x": 210, "y": 450, "width": 320, "height": 44}, "computed_role": "textbox"},
                "evidence_type": EvidenceType.SCREENSHOT,
                "evidence_title": "Element Bounding Box & Visual Inspection",
                "evidence_payload": {
                    "target_selector": "#checkout-form input[name=\"promo_code\"]",
                    "visual_hash": "a8f93e1b0c992d",
                    "viewport": "1920x1080",
                    "highlighted_element": {"tag": "input", "name": "promo_code", "placeholder": "Enter DISCOUNT2026", "accessibility_score": 98}
                },
                "metric_name": "element_locate_latency_ms",
                "metric_val": 18.5,
            },
            {
                "type": ActionType.INPUT,
                "description": "Enter test value into promo code input: 'RELIABILITY_PASS_2026'",
                "input": {"selector": "#checkout-form input[name=\"promo_code\"]", "value": "RELIABILITY_PASS_2026", "keystroke_delay_ms": 12},
                "output": {"value_set": True, "character_count": 21, "state_change": "input_validated"},
                "evidence_type": EvidenceType.CONSOLE_LOG,
                "evidence_title": "Form Input Telemetry & Console Events",
                "evidence_payload": {
                    "events": [
                        {"level": "INFO", "timestamp": "0.12s", "message": "Input focused: #checkout-form input[name='promo_code']"},
                        {"level": "INFO", "timestamp": "0.18s", "message": "Dispatched onChange event: value length 21"},
                        {"level": "DEBUG", "timestamp": "0.22s", "message": "Client validation triggered: regex matched OK"}
                    ]
                },
                "metric_name": "input_dispatch_latency_ms",
                "metric_val": 25.0,
            },
            {
                "type": ActionType.CLICK,
                "description": "Click 'Apply Promo & Continue' button: '#btn-submit-order'",
                "input": {"selector": "#btn-submit-order", "button": "left", "click_count": 1},
                "output": {"clicked": True, "event_dispatched": "click", "network_requests_triggered": 1},
                "evidence_type": EvidenceType.NETWORK_HAR,
                "evidence_title": "Network HAR Trace - Order Verification API",
                "evidence_payload": {
                    "method": "POST",
                    "endpoint": f"{target.base_url}/api/v1/orders/validate",
                    "request_headers": {"Content-Type": "application/json", "Authorization": "Bearer mock-token"},
                    "response_status": 200,
                    "response_body": {"status": "ok", "discount_applied": 0.20, "order_id": "ORD-98214-X"},
                    "network_timings": {"dns": 4.1, "connect": 12.0, "ssl": 18.4, "ttfb": 42.1, "download": 3.8}
                },
                "metric_name": "api_ttfb_latency_ms",
                "metric_val": 42.1,
            },
            {
                "type": ActionType.SUBMIT,
                "description": "Verify workflow confirmation state and transaction acknowledgement",
                "input": {"expected_state": "CONFIRMATION_SHOWN", "order_id_pattern": "^ORD-[0-9]{5}-[A-Z]$"},
                "output": {"workflow_completed": True, "confirmation_code": "ORD-98214-X", "render_time_ms": 88},
                "evidence_type": EvidenceType.LLM_TRANSCRIPT if run.test_mode == TestMode.AI_LLM_EVALUATION else EvidenceType.PERFORMANCE_TRACE,
                "evidence_title": "Workflow Assertion & Transaction Ledger Trace",
                "evidence_payload": {
                    "workflow_name": "Autonomous Checkout Verification",
                    "final_state": "SUCCESS_ACKNOWLEDGED",
                    "assertion_results": [
                        {"assertion": "Order ID format matches regex", "passed": True},
                        {"assertion": "Discount matches 20%", "passed": True},
                        {"assertion": "No unhandled exceptions in window", "passed": True}
                    ],
                    "cumulative_trace_id": f"trace_{uuid.uuid4().hex[:12]}"
                },
                "metric_name": "total_workflow_duration_ms",
                "metric_val": 315.6,
            }
        ]

        # Check if failure is simulated
        should_fail = options.simulate_failure

        for idx, step_def in enumerate(steps_plan):
            step_start = time.time()
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            is_failing_step = should_fail and (idx == len(steps_plan) - 1)

            action = TestAction(
                action_id=f"act_{uuid.uuid4().hex[:8]}",
                action_type=step_def["type"],
                description=step_def["description"],
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=ActionStatus.FAILED if is_failing_step else ActionStatus.PASSED,
                input_data=step_def["input"],
                output_data={"error": "Assertion 'Confirmation State' failed: Expected ORD-98214-X but got null response"} if is_failing_step else step_def["output"],
                duration_ms=int((time.time() - step_start) * 1000) + 15,
                error_message="Assertion failed: Server returned HTTP 500 during workflow completion" if is_failing_step else None,
            )

            # Create structured evidence
            evidence = Evidence(
                evidence_id=f"evi_{uuid.uuid4().hex[:8]}",
                run_id=run.run_id,
                action_id=action.action_id,
                evidence_type=step_def["evidence_type"],
                title=f"{'[FAILURE EVIDENCE] ' if is_failing_step else ''}{step_def['evidence_title']}",
                payload={"error_details": "Unhandled NullPointerException at OrderController.ts:84", "response_dump": {"error": "Internal Server Error", "code": 500}} if is_failing_step else step_def["evidence_payload"],
                metadata={"step_index": idx + 1, "action_type": step_def["type"].value, "is_failure": is_failing_step},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(evidence)
            action.evidence_ids.append(evidence.evidence_id)
            run.evidence_ids.append(evidence.evidence_id)

            # Record metric
            metric = Metric(
                metric_id=f"met_{uuid.uuid4().hex[:8]}",
                run_id=run.run_id,
                name=step_def["metric_name"],
                value=step_def["metric_val"],
                unit="ms",
                tags={"action_id": action.action_id, "mode": run.test_mode.value},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.metric_repo.save_metric(metric)
            run.metrics_summary[step_def["metric_name"]] = step_def["metric_val"]

            # If failure simulated on this step, record failure
            if is_failing_step:
                failure = Failure(
                    failure_id=f"fail_{uuid.uuid4().hex[:8]}",
                    run_id=run.run_id,
                    action_id=action.action_id,
                    category=FailureCategory.ASSERTION_FAILURE if run.test_mode != TestMode.AI_LLM_EVALUATION else FailureCategory.LLM_HALLUCINATION,
                    severity=Severity.HIGH,
                    title="Workflow Confirmation Assertion Failed",
                    message="Final order checkout state validation failed with HTTP 500 NullPointerException",
                    stack_trace="Traceback (most recent call last):\n  File 'app/services/checkout.ts', line 84, in handle_order\n    throw new Error('Order transaction id missing in payment response');",
                    suggested_remediation="Verify payment gateway webhook callback payload handling in 'app/services/checkout.ts' and ensure fallback transaction ID synthesis when gateway returns delayed response.",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                self.failure_repo.save_failure(failure)
                run.failure_ids.append(failure.failure_id)
                run.logs.append(f"[ERROR] Step {idx+1} failed: {failure.message}")

            run.actions.append(action)
            run.logs.append(f"[INFO] Step {idx+1} ({step_def['type'].value}) completed in {action.duration_ms}ms with status {action.status.value}")

            # If failed, break out of subsequent steps
            if is_failing_step:
                break

        total_duration = int((time.time() - start_time) * 1000)
        run.duration_ms = total_duration
        run.finished_at = datetime.now(timezone.utc).isoformat()
        run.status = RunStatus.FAILED if should_fail else RunStatus.PASSED
        run.logs.append(f"[SUMMARY] Test execution finished with status {run.status.value} in {total_duration}ms")

        self.run_repo.update_run(run)
        return run
