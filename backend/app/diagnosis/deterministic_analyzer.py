import json
import logging
from typing import Any
from pathlib import Path

from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_action import TestAction
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.enums import EvidenceType, ActionStatus, FailureCategory
from backend.app.models.diagnosis import EvidenceBundle, DeterministicSignal, ReproductionStep

logger = logging.getLogger("ai_qa_platform.deterministic_analyzer")

class DeterministicAnalyzer:
    """
    Analyzes raw test execution evidence and extracts deterministic facts & signals
    (e.g., HTTP 500s, uncaught console exceptions, missing DOM elements, failed assertions).
    Builds a curated EvidenceBundle for the LLM diagnostician.
    """

    @classmethod
    def analyze(
        cls,
        run: TestRun,
        target: ApplicationTarget | None,
        evidence_items: list[Evidence],
        failures: list[Failure],
    ) -> EvidenceBundle:
        target_id = target.target_id if target else run.application_id
        target_url = target.base_url if target else "http://localhost:3000"
        
        deterministic_signals: list[DeterministicSignal] = []
        console_errors: list[str] = []
        failed_network_calls: list[dict] = []
        page_alerts: list[str] = []
        dom_error_snippet: str | None = None

        # 1. Inspect Console Telemetry Evidence
        for evi in evidence_items:
            if evi.evidence_type in (EvidenceType.CONSOLE_LOG, "CONSOLE_LOG"):
                events = evi.payload.get("events", []) if isinstance(evi.payload, dict) else []
                for ev in events:
                    ev_type = ev.get("type", "").lower()
                    ev_text = ev.get("text", "")
                    if ev_type in ("error", "pageerror") or "uncaught" in ev_text.lower() or "500" in ev_text:
                        console_errors.append(ev_text)
                        deterministic_signals.append(
                            DeterministicSignal(
                                signal_type="CONSOLE_ERROR",
                                summary=f"Uncaught browser console error: {ev_text[:120]}",
                                details=ev,
                            )
                        )

        # 2. Inspect Network Telemetry Evidence
        for evi in evidence_items:
            if evi.evidence_type in (EvidenceType.NETWORK_HAR, "NETWORK_HAR"):
                events = evi.payload.get("events_sample", []) if isinstance(evi.payload, dict) else []
                if not events and isinstance(evi.payload, list):
                    events = evi.payload
                for ev in events:
                    if ev.get("event") == "response":
                        status_code = ev.get("status", 200)
                        if status_code >= 400 or not ev.get("ok", True):
                            failed_network_calls.append(ev)
                            deterministic_signals.append(
                                DeterministicSignal(
                                    signal_type="HTTP_ERROR",
                                    summary=f"Network request failed: HTTP {status_code} ({ev.get('status_text', '')}) on {ev.get('url', '')[:90]}",
                                    details=ev,
                                )
                            )

        # 3. Inspect DOM Snapshots for Error Banners & Alerts
        for evi in evidence_items:
            if evi.evidence_type in (EvidenceType.DOM_SNAPSHOT, "DOM_SNAPSHOT"):
                title = evi.payload.get("title", "") if isinstance(evi.payload, dict) else ""
                if "error" in title.lower() or "500" in title.lower() or "404" in title.lower():
                    page_alerts.append(f"Page title indicates error state: '{title}'")
                    deterministic_signals.append(
                        DeterministicSignal(
                            signal_type="PAGE_ALERT",
                            summary=f"Page title indicates error state: '{title}'",
                            details={"title": title, "url": evi.payload.get("url", "")},
                        )
                    )

        # 4. Inspect Failed Actions & Error Messages
        failed_action: TestAction | None = None
        failed_action_index: int | None = None

        for idx, act in enumerate(run.actions, 1):
            if act.status == ActionStatus.FAILED:
                failed_action = act
                failed_action_index = idx
                break

        # Fallback to last action if failures exist
        if not failed_action and failures and run.actions:
            failed_action = run.actions[-1]
            failed_action_index = len(run.actions)

        if failed_action and failed_action.error_message:
            err_msg = failed_action.error_message
            if "not found" in err_msg or "locator" in err_msg or "Element index" in err_msg:
                deterministic_signals.append(
                    DeterministicSignal(
                        signal_type="DOM_MISSING",
                        summary=f"Element locator unresolved or not visible: {failed_action.selector or failed_action.input_data.get('selector', 'unknown')}",
                        details={"selector": failed_action.selector, "error": err_msg},
                    )
                )
            elif "Assertion" in err_msg or "assertion" in err_msg:
                deterministic_signals.append(
                    DeterministicSignal(
                        signal_type="ASSERTION_ERROR",
                        summary=f"Assertion condition failed: {err_msg[:120]}",
                        details={"error": err_msg},
                    )
                )
            elif "timeout" in err_msg.lower():
                deterministic_signals.append(
                    DeterministicSignal(
                        signal_type="TIMEOUT",
                        summary=f"Execution step timed out: {err_msg[:120]}",
                        details={"error": err_msg},
                    )
                )
            else:
                deterministic_signals.append(
                    DeterministicSignal(
                        signal_type="ACTION_FAILED",
                        summary=f"Action [{failed_action.action_type.value}] failed: {err_msg[:120]}",
                        details={"error": err_msg, "action_type": failed_action.action_type.value},
                    )
                )

        # Also incorporate explicit Failure records
        for f in failures:
            deterministic_signals.append(
                DeterministicSignal(
                    signal_type="FAILURE_RECORD",
                    summary=f"Classified failure [{f.category.value}]: {f.message[:120]}",
                    details={"category": f.category.value, "severity": f.severity.value, "message": f.message},
                )
            )

        # Build Action History list
        action_history = [
            {
                "step": idx,
                "action": a.action_type.value,
                "description": a.description,
                "thought": a.thought,
                "selector": a.selector,
                "status": a.status.value,
                "duration_ms": a.duration_ms,
                "error": a.error_message,
            }
            for idx, a in enumerate(run.actions, 1)
        ]

        return EvidenceBundle(
            run_id=run.run_id,
            target_id=target_id,
            target_url=target_url,
            test_mode=run.test_mode.value,
            natural_language_goal=run.natural_language_goal,
            failed_action_index=failed_action_index,
            failed_action_type=failed_action.action_type.value if failed_action else None,
            failed_action_selector=failed_action.selector if failed_action else None,
            error_message=failed_action.error_message if failed_action else (failures[0].message if failures else None),
            deterministic_signals=deterministic_signals,
            action_history=action_history,
            console_errors=console_errors,
            failed_network_calls=failed_network_calls,
            page_alerts=page_alerts,
            dom_error_snippet=dom_error_snippet,
        )
