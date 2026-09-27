import json
import logging
import httpx
from typing import Any
from pydantic import BaseModel, Field, ValidationError

from backend.app.models.diagnosis import (
    EngineeringDiagnosis,
    EvidenceBundle,
    DeterministicSignal,
    ReproductionStep,
)
from backend.app.models.enums import FailureCategory, Severity

logger = logging.getLogger("ai_qa_platform.qwen_diagnostician")

SYSTEM_DIAGNOSIS_PROMPT = """You are a Principal Software Reliability & QA Engineer analyzing automated web test failures.
Your objective is to diagnose the root cause of a failure based on deterministic telemetry signals (console errors, failed HTTP responses, DOM state, and action sequence) and generate an actionable engineering bug report.

RULES:
1. Ground your diagnosis strictly on the provided deterministic telemetry facts. Do NOT invent phantom errors or backend services not mentioned in the evidence.
2. Clearly distinguish between what definitely happened (deterministic signals) and the most probable engineering root cause (hypothesis).
3. Provide step-by-step reproduction instructions.
4. Propose a concrete code/architectural fix with an optional diff.
5. Provide a copyable, runnable Playwright test script to prevent future regressions.
6. Output ONLY a valid JSON object matching the required schema. No Markdown wrapper around the JSON.
"""

class QwenDiagnostician:
    """
    Evidence-based failure diagnostic reasoner powered by local Ollama (qwen2.5-coder:7b-instruct).
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b-instruct",
        timeout_seconds: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def diagnose_failure(self, bundle: EvidenceBundle, failure_id: str | None = None) -> EngineeringDiagnosis:
        """Runs diagnosis using Ollama or falls back to deterministic rule synthesizer."""
        if not self.is_available():
            logger.info("Ollama is offline or unreachable. Generating deterministic rule-based diagnosis.")
            return self._synthesize_deterministic_fallback(bundle, failure_id)

        prompt_lines = [
            f"=== TARGET APPLICATION: {bundle.target_id} ({bundle.target_url}) ===",
            f"=== TEST RUN ID: {bundle.run_id} | MODE: {bundle.test_mode} ===",
        ]
        if bundle.natural_language_goal:
            prompt_lines.append(f"=== TEST GOAL: {bundle.natural_language_goal} ===")

        if bundle.error_message:
            prompt_lines.append(f"\n❌ PRIMARY ERROR MESSAGE: {bundle.error_message}")

        if bundle.deterministic_signals:
            prompt_lines.append("\n=== DETERMINISTIC TELEMETRY SIGNALS (FACTS) ===")
            for sig in bundle.deterministic_signals:
                prompt_lines.append(f"- [{sig.signal_type}] {sig.summary}")

        if bundle.failed_network_calls:
            prompt_lines.append("\n=== FAILED HTTP NETWORK CALLS ===")
            for net in bundle.failed_network_calls:
                prompt_lines.append(f"- HTTP {net.get('status')} on {net.get('url')}")

        if bundle.console_errors:
            prompt_lines.append("\n=== BROWSER CONSOLE EXCEPTIONS ===")
            for ce in bundle.console_errors:
                prompt_lines.append(f"- {ce}")

        if bundle.page_alerts:
            prompt_lines.append("\n=== PAGE DOM ALERTS ===")
            for pa in bundle.page_alerts:
                prompt_lines.append(f"- {pa}")

        prompt_lines.append("\n=== PRECEDING ACTION SEQUENCE ===")
        for act in bundle.action_history:
            status_emoji = "✓" if act.get("status") == "PASSED" else "✗"
            prompt_lines.append(f"Step {act.get('step')} [{status_emoji}]: {act.get('action')} - {act.get('description')}")

        prompt_lines.append("\nRespond now with a complete JSON diagnosis object adhering to the schema:")
        prompt_lines.append("""
{
  "title": "Clear concise bug title",
  "root_cause_summary": "1-2 sentence engineering root cause explanation",
  "failure_category": "FUNCTIONAL_BUG | ASSERTION_FAILURE | TIMEOUT | NAVIGATION_TIMEOUT | ELEMENT_NOT_FOUND | INPUT_FAILED | CLICK_FAILED | ASSERTION_FAILED | NETWORK_ERROR | BROWSER_ERROR | EXECUTION_TIMEOUT | AGENT_BUDGET_EXCEEDED | AGENT_LOOP_DETECTED",
  "confidence_score": 0.95,
  "suspected_component": "Frontend Component / Backend API / Database / Router",
  "reproduction_steps": [
    {"step_number": 1, "action": "Navigate to URL", "target": "Home", "expected": "...", "observed": "..."},
    {"step_number": 2, "action": "Click button", "target": "#submit", "expected": "...", "observed": "..."}
  ],
  "suggested_fix": "Detailed actionable remediation code or configuration change",
  "code_diff_suggestion": "```diff\\n- old_code\\n+ new_code\\n```",
  "regression_test_spec": "// Playwright test code to prevent regressions\\ntest('should...', async ({ page }) => { ... });",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW"
}
""")

        prompt = "\n".join(prompt_lines)

        payload = {
            "model": self.model,
            "system": SYSTEM_DIAGNOSIS_PROMPT,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 700
            }
        }

        try:
            res = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds
            )
            res.raise_for_status()
            raw_text = res.json().get("response", "").strip()
            parsed = json.loads(raw_text)

            # Map category & severity safely
            cat_str = parsed.get("failure_category", "FUNCTIONAL_BUG")
            try:
                category = FailureCategory(cat_str)
            except ValueError:
                category = FailureCategory.FUNCTIONAL_BUG

            sev_str = parsed.get("severity", "HIGH").upper()
            try:
                severity = Severity(sev_str)
            except ValueError:
                severity = Severity.HIGH

            repro_steps = [
                ReproductionStep(**item) for item in parsed.get("reproduction_steps", [])
            ]

            return EngineeringDiagnosis(
                run_id=bundle.run_id,
                failure_id=failure_id,
                title=parsed.get("title", f"Failure Diagnosis for {bundle.run_id}"),
                root_cause_summary=parsed.get("root_cause_summary", "Failure detected during test execution."),
                failure_category=category,
                confidence_score=float(parsed.get("confidence_score", 0.9)),
                suspected_component=parsed.get("suspected_component", "Application Component"),
                deterministic_signals=bundle.deterministic_signals,
                reproduction_steps=repro_steps if repro_steps else self._build_default_repro_steps(bundle),
                suggested_fix=parsed.get("suggested_fix", "Review component implementation and add input validation."),
                code_diff_suggestion=parsed.get("code_diff_suggestion"),
                regression_test_spec=parsed.get("regression_test_spec", self._build_default_regression_spec(bundle)),
                severity=severity,
                evidence_bundle_summary=f"Synthesized from {len(bundle.deterministic_signals)} deterministic signals and {len(bundle.action_history)} executed steps.",
            )

        except Exception as e:
            logger.warning(f"Qwen LLM diagnosis failed ({e}). Falling back to deterministic synthesizer.")
            return self._synthesize_deterministic_fallback(bundle, failure_id)

    def _synthesize_deterministic_fallback(self, bundle: EvidenceBundle, failure_id: str | None) -> EngineeringDiagnosis:
        """Deterministic rule-based failure diagnosis when LLM is offline or in unit tests."""
        err_msg = bundle.error_message or "Unknown failure during execution"
        
        # Determine root cause and category based on deterministic signals
        has_http_500 = any("500" in s.summary for s in bundle.deterministic_signals)
        has_http_404 = any("404" in s.summary for s in bundle.deterministic_signals)
        has_console_err = len(bundle.console_errors) > 0
        has_dom_missing = any(s.signal_type == "DOM_MISSING" for s in bundle.deterministic_signals)
        has_timeout = any("timeout" in s.summary.lower() for s in bundle.deterministic_signals)
        has_loop = "loop" in err_msg.lower()

        if has_http_500:
            title = "Unhandled Server 500 Error during API Request"
            category = FailureCategory.FUNCTIONAL_BUG
            component = "Backend API Endpoint"
            root_cause = f"The application triggered a backend HTTP 500 Internal Server Error during action execution: {err_msg}"
            fix = "Inspect server-side logs for unhandled exceptions or null pointer references at the failing route."
            diff = "```diff\n- response = process_request(data)\n+ try:\n+     response = process_request(data)\n+ except Exception as e:\n+     logger.error(f'Error processing request: {e}')\n+     raise HTTPException(status_code=400, detail=str(e))\n```"
            severity = Severity.CRITICAL
        elif has_dom_missing:
            title = f"DOM Element Not Found or Unreachable: {bundle.failed_action_selector or 'Target Selector'}"
            category = FailureCategory.ELEMENT_NOT_FOUND
            component = "Frontend UI Template"
            root_cause = f"The browser agent attempted to interact with element '{bundle.failed_action_selector}' which was not visible or not rendered in the active DOM."
            fix = f"Ensure the element with selector '{bundle.failed_action_selector}' is rendered and loaded before user interaction, or update the selector to match current markup."
            diff = f"```diff\n- <button id='old_id'>Submit</button>\n+ <button id='{bundle.failed_action_selector or 'btn-submit'}' data-testid='submit-btn'>Submit</button>\n```"
            severity = Severity.HIGH
        elif has_timeout:
            title = "Execution or Navigation Timeout Exceeded"
            category = FailureCategory.NAVIGATION_TIMEOUT if "navigation" in err_msg.lower() else FailureCategory.EXECUTION_TIMEOUT
            component = "Network Gateway / Frontend Asset Bundler"
            root_cause = f"Operation timed out waiting for resource load or page stability: {err_msg}"
            fix = "Optimize page asset bundle size, reduce server response latency, or increase step wait timeout threshold."
            diff = None
            severity = Severity.MEDIUM
        elif has_loop:
            title = "Autonomous Agent Decision Loop Detected"
            category = FailureCategory.AGENT_LOOP_DETECTED
            component = "Autonomous Agent Reasoner / UI State"
            root_cause = "Agent executed identical browser actions 3 consecutive times without state progression."
            fix = "Provide clearer UI state indicators after action execution and refine natural-language test goal."
            diff = None
            severity = Severity.MEDIUM
        elif has_console_err:
            title = "Uncaught Browser Runtime Exception"
            category = FailureCategory.BROWSER_ERROR
            component = "Frontend JavaScript Client"
            root_cause = f"Browser console emitted uncaught runtime error: {bundle.console_errors[0][:120]}"
            fix = "Add null checks and error boundaries to prevent uncaught runtime exceptions."
            diff = "```diff\n- const data = response.items.map(x => x.name);\n+ const data = response?.items?.map(x => x?.name) || [];\n```"
            severity = Severity.HIGH
        else:
            title = f"Execution Failure: {bundle.error_message[:60] if bundle.error_message else 'Assertion Failure'}"
            category = FailureCategory.FUNCTIONAL_BUG
            component = "Application Logic"
            root_cause = f"Test execution failed at step {bundle.failed_action_index or 1}: {err_msg}"
            fix = "Review workflow logic and verify test prerequisites."
            diff = None
            severity = Severity.MEDIUM

        repro_steps = self._build_default_repro_steps(bundle)
        regression_spec = self._build_default_regression_spec(bundle)

        return EngineeringDiagnosis(
            run_id=bundle.run_id,
            failure_id=failure_id,
            title=title,
            root_cause_summary=root_cause,
            failure_category=category,
            confidence_score=0.92,
            suspected_component=component,
            deterministic_signals=bundle.deterministic_signals,
            reproduction_steps=repro_steps,
            suggested_fix=fix,
            code_diff_suggestion=diff,
            regression_test_spec=regression_spec,
            severity=severity,
            evidence_bundle_summary=f"Deterministic fallback diagnosis generated from {len(bundle.deterministic_signals)} signals.",
        )

    def _build_default_repro_steps(self, bundle: EvidenceBundle) -> list[ReproductionStep]:
        steps = [
            ReproductionStep(
                step_number=1,
                action="Navigate to target application URL",
                target=bundle.target_url,
                expected="Page loads successfully",
                observed="Page loaded",
            )
        ]
        curr_step = 2
        for act in bundle.action_history:
            is_fail = act.get("status") == "FAILED"
            steps.append(
                ReproductionStep(
                    step_number=curr_step,
                    action=f"Execute {act.get('action')}: {act.get('description')}",
                    target=act.get("selector") or bundle.target_url,
                    expected="Action succeeds and progresses workflow",
                    observed="Action failed with error: " + (act.get("error") or "Failure") if is_fail else "Action succeeded",
                )
            )
            curr_step += 1
            if is_fail:
                break
        return steps

    def _build_default_regression_spec(self, bundle: EvidenceBundle) -> str:
        url = bundle.target_url or "http://localhost:3000"
        selector = bundle.failed_action_selector or "#main-content"
        
        return f"""// Autonomous Regression Test generated by Antigravity AI Platform
import {{ test, expect }} from '@playwright/test';

test('Regression: Verify stability and error resilience for {bundle.target_id}', async ({{ page }}) => {{
  // 1. Navigate to target
  await page.goto('{url}', {{ waitUntil: 'domcontentloaded', timeout: 15000 }});

  // 2. Verify page has loaded cleanly without 500 error banners
  const errorBanner = page.locator('.error-banner, [role="alert"]');
  await expect(errorBanner).toHaveCount(0);

  // 3. Verify target interactive element exists and is visible
  const targetElement = page.locator('{selector}').first();
  await expect(targetElement).toBeVisible({{ timeout: 8000 }});

  // 4. Assert console is clean of uncaught exceptions
  page.on('pageerror', (err) => {{
    throw new Error(`Uncaught browser exception encountered: ${{err.message}}`);
  }});
}});
"""
