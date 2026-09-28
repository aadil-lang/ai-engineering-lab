import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from backend.app.dogfooding.live_events import LiveEventType
from backend.app.dogfooding.live_session_bus import live_event_bus
from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget

logger = logging.getLogger("ai_qa_platform.runner_observer")

class LiveRunnerObserver:
    """
    Observability adapter attached to authoritative test runners
    (AIAgentTestRunner, PlaywrightTestRunner).
    Emits structured live events and updates live session state without
    affecting runner execution authority or control flow.
    """

    def __init__(self, session_id: str, run_id: str):
        self.session_id = session_id
        self.run_id = run_id

    @classmethod
    def for_run(
        cls,
        run: TestRun,
        target: Optional[ApplicationTarget] = None,
        total_steps: int = 10,
    ) -> "LiveRunnerObserver":
        # Look up existing session or create a new one
        existing = live_event_bus.get_session_by_run_id(run.run_id)
        if existing:
            return cls(session_id=existing.session_id, run_id=run.run_id)

        target_id = getattr(target, "target_id", None) or run.application_id or "target_default"
        app_id = run.application_id or getattr(target, "application_id", None) or getattr(target, "target_id", "app_default")
        runner_type = run.runner_type.value if hasattr(run.runner_type, "value") else str(run.runner_type)
        execution_source = run.execution_source.value if hasattr(run.execution_source, "value") else str(run.execution_source)

        session = live_event_bus.create_session(
            run_id=run.run_id,
            target_id=target_id,
            application_id=app_id,
            test_case_id=run.test_case_id,
            runner_type=runner_type,
            execution_source=execution_source,
            total_steps=total_steps,
        )
        return cls(session_id=session.session_id, run_id=run.run_id)

    def on_session_start(self, target_url: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.SESSION_STARTED,
            payload={"target_url": target_url},
        )

    def on_navigation_start(self, url: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.NAVIGATION_STARTED,
            payload={"url": url},
        )

    def on_navigation_complete(self, url: str, title: Optional[str] = None):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.NAVIGATION_COMPLETED,
            payload={"url": url, "title": title},
        )

    def on_dom_observed(
        self,
        step_index: int,
        element_count: int,
        interactive_elements: Optional[list] = None,
        url: Optional[str] = None,
    ):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.DOM_OBSERVED,
            payload={
                "step_index": step_index,
                "element_count": element_count,
                "interactive_elements": interactive_elements or [],
                "url": url,
            },
        )

    def on_action_start(
        self,
        action_type: str,
        description: str,
        step_index: Optional[int] = None,
        selector: Optional[str] = None,
        value: Optional[str] = None,
    ):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.ACTION_STARTED,
            payload={
                "action_type": action_type,
                "description": description,
                "step_index": step_index,
                "selector": selector,
                "value": value,
            },
        )

    def on_action_complete(
        self,
        action_type: str,
        description: str,
        step_index: Optional[int] = None,
        status: str = "PASSED",
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ):
        event_type = LiveEventType.ACTION_COMPLETED if status == "PASSED" else LiveEventType.ACTION_FAILED
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=event_type,
            payload={
                "action_type": action_type,
                "description": description,
                "step_index": step_index,
                "status": status,
                "error": error,
                "duration_ms": duration_ms,
            },
        )

    def on_screenshot(
        self,
        screenshot_bytes: bytes,
        screenshot_id: Optional[str] = None,
        step_index: Optional[int] = None,
    ):
        sc_id = screenshot_id or f"sc_{uuid.uuid4().hex[:8]}"
        live_event_bus.store_latest_screenshot(self.session_id, screenshot_bytes, sc_id)
        # Also publish event with base64 for real-time frontend canvas updates
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.SCREENSHOT_CAPTURED,
            payload={
                "screenshot_id": sc_id,
                "step_index": step_index,
                "screenshot_base64": b64,
                "size_bytes": len(screenshot_bytes),
            },
        )

    def on_console(self, log_entry: Dict[str, Any]):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.CONSOLE_EVENT,
            payload=log_entry,
        )

    def on_page_error(self, error_text: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.PAGE_ERROR,
            payload={"error": error_text},
        )

    def on_network_request(self, req_info: Dict[str, Any]):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.NETWORK_REQUEST_STARTED,
            payload=req_info,
        )

    def on_network_response(self, res_info: Dict[str, Any]):
        is_ok = res_info.get("ok", True)
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.NETWORK_REQUEST_COMPLETED if is_ok else LiveEventType.NETWORK_REQUEST_FAILED,
            payload=res_info,
        )

    def on_performance(self, metrics: Dict[str, Any]):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.PERFORMANCE_UPDATE,
            payload=metrics,
        )

    def on_assertion(
        self,
        assertion_name: str,
        passed: bool,
        detail: Optional[str] = None,
    ):
        event_type = LiveEventType.ASSERTION_PASSED if passed else LiveEventType.ASSERTION_FAILED
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=event_type,
            payload={
                "assertion": assertion_name,
                "passed": passed,
                "detail": detail,
            },
        )

    def on_deterministic_evaluation(self, status: str, details: Optional[Dict] = None):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.DETERMINISTIC_EVALUATION_COMPLETED,
            payload={
                "evaluation_status": status,
                "details": details or {},
            },
        )

    def on_diagnosis(self, diagnosis_id: str, summary: Optional[str] = None):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.DIAGNOSIS_COMPLETED,
            payload={
                "diagnosis_id": diagnosis_id,
                "summary": summary,
            },
        )

    def on_remediation(self, task_id: str, title: Optional[str] = None):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.REMEDIATION_PROPOSED,
            payload={
                "task_id": task_id,
                "title": title,
            },
        )

    def on_strategy_planned(self, strategy_data: Dict[str, Any]):
        sanitized = {k: v for k, v in strategy_data.items() if k not in ("chain_of_thought", "reasoning_content", "prompt_template")}
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.STRATEGY_PLANNED,
            payload=sanitized,
        )

    def on_strategy_adapted(self, adaptation_data: Dict[str, Any]):
        sanitized = {k: v for k, v in adaptation_data.items() if k not in ("chain_of_thought", "reasoning_content", "prompt_template")}
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.STRATEGY_ADAPTED,
            payload=sanitized,
        )

    def on_retest(self, transition: str, comparisons: Optional[list] = None):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.RETEST_COMPLETED,
            payload={
                "transition": transition,
                "comparisons": comparisons or [],
            },
        )

    def on_session_complete(self, status: str = "PASSED", duration_ms: int = 0):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.SESSION_COMPLETED,
            payload={"status": status, "duration_ms": duration_ms},
        )

    def on_session_fail(self, error_message: str, duration_ms: int = 0):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.SESSION_FAILED,
            payload={"error": error_message, "duration_ms": duration_ms},
        )

    # Slice 8E Memory Observers
    def on_memory_retrieval_started(self, query: str, application_id: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_RETRIEVAL_STARTED,
            payload={"query": query, "application_id": application_id},
        )

    def on_memory_retrieval_completed(
        self,
        total_retrieved: int,
        applicable_count: int,
        historical_count: int,
        conflicting_count: int,
        top_memories: list,
    ):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_RETRIEVAL_COMPLETED,
            payload={
                "total_retrieved": total_retrieved,
                "applicable_count": applicable_count,
                "historical_count": historical_count,
                "conflicting_count": conflicting_count,
                "top_memories": top_memories,
            },
        )

    def on_memory_candidate_created(self, candidate_id: str, memory_type: str, content: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_CANDIDATE_CREATED,
            payload={"candidate_id": candidate_id, "memory_type": memory_type, "content": content},
        )

    def on_memory_promoted(self, memory_id: str, memory_type: str, content: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_PROMOTED,
            payload={"memory_id": memory_id, "memory_type": memory_type, "content": content},
        )

    def on_memory_invalidated(self, memory_id: str, reason: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_INVALIDATED,
            payload={"memory_id": memory_id, "reason": reason},
        )

    def on_memory_contradiction_detected(self, current_memory_id: str, contradicted_memory_id: str, rationale: str):
        live_event_bus.publish(
            session_id=self.session_id,
            event_type=LiveEventType.MEMORY_CONTRADICTION_DETECTED,
            payload={
                "current_memory_id": current_memory_id,
                "contradicted_memory_id": contradicted_memory_id,
                "rationale": rationale,
            },
        )

