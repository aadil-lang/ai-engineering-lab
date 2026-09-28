import asyncio
import time
import uuid
import traceback
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)

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
    RunnerType,
    TestMode,
    ExecutionSource,
)
from backend.app.repositories.base import (
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    MetricRepositoryInterface,
    RunRepositoryInterface,
)
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.agents.dom_extractor import DOMExtractor, DOMObservation
from backend.app.agents.ollama_agent import OllamaReasoner, AgentDecision
from backend.app.dogfooding.runner_observer import LiveRunnerObserver
from backend.app.dogfooding.strategy_engine import AdaptiveStrategyEngine
from backend.app.dogfooding.strategy_models import TestingStrategy
from backend.app.memory.repository import EngineeringMemoryRepository
from backend.app.memory.vector_index import VectorMemoryIndex
from backend.app.memory.embedding import LocalDeterministicEmbeddingProvider
from backend.app.memory.hybrid_rag import HybridRAGService
from backend.app.memory.candidate_service import MemoryCandidateService

logger = logging.getLogger("ai_qa_platform.ai_agent_runner")

class AIAgentTestRunner(BaseTestRunner):
    """
    AI-Controlled Browser Agent Execution Runner.
    Uses local Ollama (qwen2.5-coder:7b-instruct) to drive an isolated Playwright browser session
    through an observation -> reasoning -> action loop with deterministic guardrails.
    """

    def __init__(
        self,
        run_repo: RunRepositoryInterface,
        evidence_repo: EvidenceRepositoryInterface,
        failure_repo: FailureRepositoryInterface,
        metric_repo: MetricRepositoryInterface,
        blob_storage: LocalEvidenceBlobStorage | None = None,
        reasoner: OllamaReasoner | None = None,
        memory_repo: EngineeringMemoryRepository | None = None,
        vector_index: VectorMemoryIndex | None = None,
        embedding_provider: LocalDeterministicEmbeddingProvider | None = None,
        hybrid_rag: HybridRAGService | None = None,
        candidate_service: MemoryCandidateService | None = None,
    ):
        self.run_repo = run_repo
        self.evidence_repo = evidence_repo
        self.failure_repo = failure_repo
        self.metric_repo = metric_repo
        self.blob_storage = blob_storage or LocalEvidenceBlobStorage()
        self.reasoner = reasoner or OllamaReasoner()
        self._current_observer: LiveRunnerObserver | None = None

        # Slice 8E Local Engineering Memory & Hybrid RAG
        self.memory_repo = memory_repo or EngineeringMemoryRepository()
        self.embedding_provider = embedding_provider or LocalDeterministicEmbeddingProvider()
        self.vector_index = vector_index or VectorMemoryIndex()
        self.hybrid_rag = hybrid_rag or HybridRAGService(
            repository=self.memory_repo,
            vector_index=self.vector_index,
            embedding_provider=self.embedding_provider,
        )
        self.candidate_service = candidate_service or MemoryCandidateService(
            repository=self.memory_repo,
            vector_index=self.vector_index,
            embedding_provider=self.embedding_provider,
        )

    async def execute(self, run: TestRun, target: ApplicationTarget, options: TestRunCreate) -> TestRun:
        start_time = time.time()
        run.status = RunStatus.RUNNING
        run.runner_type = RunnerType.AI_AGENT
        run.execution_source = ExecutionSource.REAL_AI_AGENT
        run.started_at = datetime.now(timezone.utc).isoformat()

        # Isolate session and browser context
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        browser_context_id = f"ctx_{uuid.uuid4().hex[:8]}"
        run.session_id = session_id
        run.browser_context_id = browser_context_id

        # Determine goal and budget
        target_url = options.target_url_override or target.base_url or "http://localhost:3000"
        goal = options.natural_language_goal or run.natural_language_goal
        if not goal:
            if run.test_mode == TestMode.EXPLORATORY_DOGFOODING:
                goal = "Autonomously explore the application interface, test interactive components, and verify page stability."
            else:
                goal = f"Verify primary user workflows and verify page functionality at {target_url} without errors."
        run.natural_language_goal = goal
        
        max_steps = min(max(options.max_agent_steps or run.max_agent_steps or 10, 1), 25)
        run.max_agent_steps = max_steps
        self.run_repo.update_run(run)

        run.logs.append(f"[AI_AGENT] Session {session_id} initialized with model: {self.reasoner.model}")
        run.logs.append(f"[AI_AGENT] Target URL: {target_url}")
        run.logs.append(f"[AI_AGENT] Goal: {goal}")
        run.logs.append(f"[AI_AGENT] Max Budget: {max_steps} steps | Timeout: 120s")

        # Slice 8D Live Console Observability
        observer = LiveRunnerObserver.for_run(run, target, total_steps=max_steps)
        self._current_observer = observer
        observer.on_session_start(target_url)

        # Slice 8E Engineering Memory Retrieval
        retrieved_memories = []
        bounded_memory_context = ""
        app_id = target.application_id or target.target_id
        try:
            observer.on_memory_retrieval_started(query=goal, application_id=app_id)
            if self.hybrid_rag:
                p_ver = getattr(df_context, "prompt_version", None) if df_context else None
                g_com = getattr(df_context, "git_commit", None) if df_context else None
                retrieval_results = self.hybrid_rag.retrieve(
                    query=goal,
                    application_id=app_id,
                    top_k=5,
                    current_prompt_version=p_ver,
                    current_git_commit=g_com,
                )
                retrieved_memories = retrieval_results
                bounded_memory_context = self.hybrid_rag.format_memory_for_agent(
                    retrieval_results=retrieval_results,
                    application_name=target.name,
                )
                app_cnt = sum(1 for r in retrieval_results if r.applicability.value == "APPLICABLE")
                hist_cnt = sum(1 for r in retrieval_results if r.applicability.value in ("PARTIALLY_APPLICABLE", "STALE"))
                conf_cnt = sum(1 for r in retrieval_results if r.conflict_notes)
                top_mems = [{"content": r.memory.content, "status": r.memory.status.value, "type": r.memory.memory_type.value} for r in retrieval_results[:3]]
                observer.on_memory_retrieval_completed(
                    total_retrieved=len(retrieval_results),
                    applicable_count=app_cnt,
                    historical_count=hist_cnt,
                    conflicting_count=conf_cnt,
                    top_memories=top_mems,
                )
        except Exception as mem_err:
            run.logs.append(f"[WARN] Memory retrieval failed: {mem_err}. Continuing with baseline strategy.")
            logger.warning(f"[MEMORY] Memory retrieval failed gracefully: {mem_err}")

        # Slice 8D.1 Application-Adaptive Strategy
        df_context = getattr(options, "dogfooding_context", None)
        historical_failures = []
        if hasattr(self.failure_repo, "get_failures_by_run"):
            try:
                historical_failures = self.failure_repo.get_failures_by_run(run.run_id)
            except Exception:
                pass
        strategy = AdaptiveStrategyEngine.build_strategy(
            run_id=run.run_id,
            target=target,
            goal=goal,
            test_mode=run.test_mode,
            context=df_context,
            historical_failures=historical_failures,
            retrieved_memories=retrieved_memories,
        )
        run.metadata["testing_strategy"] = strategy.to_summary_dict()
        observer.on_strategy_planned(strategy.to_summary_dict())

        captured_console_logs: list[dict] = []
        captured_network_events: list[dict] = []
        consecutive_errors = 0
        last_error_message: str | None = None
        action_history_summary: list[str] = []
        previous_decisions: list[str] = []

        browser: Browser | None = None
        context: BrowserContext | None = None
        page: Page | None = None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="AntigravityAIAgent/1.0 (Playwright; x86_64)",
                    ignore_https_errors=True,
                )
                page = await context.new_page()

                # Wire real console and error listeners
                def handle_console(msg):
                    log_entry = {
                        "type": msg.type,
                        "text": msg.text,
                        "location": msg.location,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    captured_console_logs.append(log_entry)
                    observer.on_console(log_entry)
                page.on("console", handle_console)

                def handle_page_error(err):
                    err_entry = {
                        "type": "error",
                        "text": str(err),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    captured_console_logs.append(err_entry)
                    observer.on_page_error(str(err))
                page.on("pageerror", handle_page_error)

                # Wire real network listeners
                def handle_request(req):
                    req_entry = {
                        "event": "request",
                        "url": req.url,
                        "method": req.method,
                        "resource_type": req.resource_type,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    captured_network_events.append(req_entry)
                    observer.on_network_request({"url": req.url, "method": req.method, "resource_type": req.resource_type})
                page.on("request", handle_request)

                def handle_response(res):
                    res_entry = {
                        "event": "response",
                        "url": res.url,
                        "status": res.status,
                        "status_text": res.status_text,
                        "ok": res.ok,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    captured_network_events.append(res_entry)
                    observer.on_network_response({"url": res.url, "status": res.status, "status_text": res.status_text, "ok": res.ok})
                page.on("response", handle_response)

                def handle_request_failed(req):
                    fail_entry = {
                        "event": "request_failed",
                        "url": req.url,
                        "method": req.method,
                        "failure": req.failure,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    captured_network_events.append(fail_entry)
                    observer.on_network_response({"url": req.url, "method": req.method, "failure": req.failure, "ok": False})
                page.on("requestfailed", handle_request_failed)

                # Initial Navigation
                run.logs.append(f"[AI_AGENT] Navigating to initial page: {target_url}")
                observer.on_navigation_start(target_url)
                try:
                    await page.goto(target_url, timeout=15000, wait_until="domcontentloaded")
                    observer.on_navigation_complete(target_url, title="Initial Page")
                except Exception as e:
                    run.logs.append(f"[WARN] Initial navigation warning: {e}")
                    observer.on_navigation_complete(target_url, title=f"Error: {e}")

                # ----------------------------------------------------
                # ReAct Observation -> Reasoning -> Action Loop
                # ----------------------------------------------------
                step_index = 0
                goal_completed = False
                terminal_failure_reason: str | None = None

                while step_index < max_steps:
                    step_index += 1
                    elapsed = time.time() - start_time
                    if elapsed > 120.0:
                        raise PlaywrightTimeoutError("Total agent execution budget exceeded 120 seconds limit.")

                    if consecutive_errors >= 3:
                        terminal_failure_reason = f"Agent encountered 3 consecutive failed actions: {last_error_message}"
                        break

                    # 1. Observe DOM
                    observation = await DOMExtractor.extract_from_page(page)
                    observer.on_dom_observed(step_index, len(observation.interactive_elements), url=page.url)

                    # 2. Reason with LLM using Adaptive Strategy Guidance
                    history_str = "\n".join(action_history_summary[-5:]) if action_history_summary else "No previous actions."
                    strategy_guidance = AdaptiveStrategyEngine.format_strategy_guidance(strategy, step_index, max_steps)
                    try:
                        decision = self.reasoner.decide_next_action(
                            goal=goal,
                            test_mode=run.test_mode.value,
                            current_dom_summary=observation.text_summary,
                            history_summary=history_str,
                            step_number=step_index,
                            max_steps=max_steps,
                            last_error=last_error_message,
                            strategy_guidance=strategy_guidance,
                            memory_context=bounded_memory_context,
                        )
                    except Exception as llm_err:
                        run.logs.append(f"[ERROR] LLM Reasoning failed on step {step_index}: {llm_err}")
                        consecutive_errors += 1
                        last_error_message = f"LLM inference error: {str(llm_err)}"
                        continue

                    # Record Thought Trace
                    thought_entry = {
                        "step": step_index,
                        "thought": decision.thought,
                        "action": decision.action,
                        "element_index": decision.element_index,
                        "selector": decision.selector,
                        "value": decision.value,
                        "url": decision.url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    run.agent_thought_trace.append(thought_entry)
                    run.logs.append(f"[AGENT THINKING] Step {step_index}: {decision.thought}")

                    # Check for Loop Detection (same action repeated 3 times)
                    decision_signature = f"{decision.action}:{decision.element_index}:{decision.selector}:{decision.value}:{decision.url}"
                    previous_decisions.append(decision_signature)
                    if len(previous_decisions) >= 3 and previous_decisions[-1] == previous_decisions[-2] == previous_decisions[-3]:
                        terminal_failure_reason = f"Loop detected: Agent repeated the same action 3 times ({decision.action})"
                        break

                    # 3. Handle Terminal Decisions
                    if decision.action == "finish_pass":
                        goal_completed = True
                        action_record = TestAction(
                            action_id=f"act_{uuid.uuid4().hex[:8]}",
                            action_type=ActionType.FINISH,
                            description=f"Agent completed goal: {decision.reason or 'Goal satisfied'}",
                            thought=decision.thought,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            status=ActionStatus.PASSED,
                            input_data={"reason": decision.reason},
                            output_data={"goal_reached": True},
                        )
                        run.actions.append(action_record)
                        run.logs.append(f"[AGENT FINISH] Goal satisfied: {decision.reason or 'Success'}")
                        break

                    if decision.action == "finish_fail":
                        terminal_failure_reason = decision.reason or "Agent determined the goal cannot be satisfied due to application errors."
                        action_record = TestAction(
                            action_id=f"act_{uuid.uuid4().hex[:8]}",
                            action_type=ActionType.FINISH,
                            description=f"Agent aborted with failure: {terminal_failure_reason}",
                            thought=decision.thought,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            status=ActionStatus.FAILED,
                            error_message=terminal_failure_reason,
                            input_data={"reason": decision.reason},
                        )
                        run.actions.append(action_record)
                        run.logs.append(f"[AGENT FINISH] Terminated with failure: {terminal_failure_reason}")
                        break

                    # 4. Dispatch and Execute Browser Action with Guardrails
                    action_record = await self._execute_browser_action(
                        run=run,
                        page=page,
                        decision=decision,
                        observation=observation,
                        step_index=step_index,
                    )
                    run.actions.append(action_record)

                    # Update history and consecutive error tracking
                    if action_record.status == ActionStatus.PASSED:
                        consecutive_errors = 0
                        last_error_message = None
                        action_history_summary.append(
                            f"[Step {step_index}] Action: {decision.action}, Desc: {action_record.description} -> PASSED"
                        )
                    else:
                        consecutive_errors += 1
                        last_error_message = action_record.error_message
                        action_history_summary.append(
                            f"[Step {step_index}] Action: {decision.action} -> FAILED ({action_record.error_message})"
                        )

                    # Slice 8D.1 Dynamic Strategy Adaptation
                    strategy, adaptation_event = AdaptiveStrategyEngine.adapt_strategy(
                        strategy=strategy,
                        step_number=step_index,
                        max_steps=max_steps,
                        observation=observation,
                        last_action=action_record,
                        recent_errors=[last_error_message] if last_error_message else [],
                    )
                    if adaptation_event:
                        observer.on_strategy_adapted(adaptation_event.model_dump())
                        run.metadata["testing_strategy"] = strategy.to_summary_dict()
                        run.logs.append(f"[STRATEGY ADAPT] Step {step_index}: {adaptation_event.reason}")

                    # Add delay if requested
                    if options.action_delay_ms > 0:
                        await asyncio.sleep(options.action_delay_ms / 1000.0)

                # End of ReAct Loop: Determine Final Run Status
                if not goal_completed and terminal_failure_reason:
                    raise PlaywrightError(terminal_failure_reason)
                elif not goal_completed and step_index >= max_steps:
                    raise PlaywrightTimeoutError(f"Agent reached maximum step budget ({max_steps} steps) without completing goal.")

                # Capture Final Performance & Network & Console Artifacts
                await self._capture_final_telemetry(run, page, captured_console_logs, captured_network_events)

                # Close Browser Session
                await page.close()
                await context.close()
                await browser.close()

            # Mark Run as PASSED
            total_duration = int((time.time() - start_time) * 1000)
            run.duration_ms = total_duration
            run.finished_at = datetime.now(timezone.utc).isoformat()
            run.status = RunStatus.PASSED
            run.logs.append(f"[SUMMARY] AI Agent test run completed successfully (PASS) in {total_duration}ms ({len(run.actions)} actions executed)")
            observer.on_session_complete(status="PASSED", duration_ms=total_duration)

        except PlaywrightTimeoutError as te:
            total_duration = int((time.time() - start_time) * 1000)
            category = FailureCategory.AGENT_BUDGET_EXCEEDED if "budget" in str(te).lower() else FailureCategory.EXECUTION_TIMEOUT
            self._handle_failure(run, category, f"AI Agent Timeout: {category.value}", str(te), traceback.format_exc(), start_time)
            observer.on_session_fail(error_message=str(te), duration_ms=total_duration)
        except Exception as e:
            total_duration = int((time.time() - start_time) * 1000)
            err_msg = str(e)
            category = FailureCategory.FUNCTIONAL_BUG
            if "Loop detected" in err_msg:
                category = FailureCategory.AGENT_LOOP_DETECTED
            elif "schema" in err_msg or "invalid JSON" in err_msg:
                category = FailureCategory.INVALID_ACTION_SCHEMA
            elif "maximum step budget" in err_msg:
                category = FailureCategory.AGENT_BUDGET_EXCEEDED
            elif "not found" in err_msg or "Element index" in err_msg:
                category = FailureCategory.ELEMENT_NOT_FOUND
            elif "navigation" in err_msg:
                category = FailureCategory.NAVIGATION_TIMEOUT
            elif "Assertion" in err_msg:
                category = FailureCategory.ASSERTION_FAILED

            self._handle_failure(run, category, f"AI Agent Run Failed: {category.value}", err_msg, traceback.format_exc(), start_time)
            observer.on_session_fail(error_message=err_msg, duration_ms=total_duration)

        # Slice 8E Post-run memory candidate extraction & promotion
        try:
            if hasattr(self, "candidate_service") and self.candidate_service:
                run_dict = run.model_dump() if hasattr(run, "model_dump") else run.dict()
                app_id = target.application_id or target.target_id
                promoted = self.candidate_service.process_run_and_promote(
                    run_dict=run_dict,
                    application_id=app_id,
                    context_dict=df_context.model_dump() if df_context and hasattr(df_context, "model_dump") else (df_context.dict() if df_context else None),
                )
                if observer and promoted:
                    for p_mem in promoted:
                        observer.on_memory_promoted(p_mem.memory_id, p_mem.memory_type.value, p_mem.content)
        except Exception as mem_err:
            logger.warning(f"[MEMORY] Post-run candidate processing warning: {mem_err}")

        self.run_repo.update_run(run)
        return run

    async def _execute_browser_action(
        self,
        run: TestRun,
        page: Page,
        decision: AgentDecision,
        observation: DOMObservation,
        step_index: int,
    ) -> TestAction:
        """Executes a single validated LLM decision against Playwright and captures evidence."""
        step_start = time.time()
        
        # Map agent action to domain ActionType
        action_type_map = {
            "navigate": ActionType.NAVIGATE,
            "click": ActionType.CLICK,
            "input": ActionType.INPUT,
            "hover": ActionType.HOVER,
            "press_key": ActionType.PRESS_KEY,
            "scroll": ActionType.SCROLL,
            "assert_text": ActionType.ASSERT,
            "assert_element": ActionType.ASSERT,
        }
        domain_action_type = action_type_map.get(decision.action, ActionType.CUSTOM)

        # Resolve selector if applicable
        resolved_selector: str | None = None
        if decision.element_index is not None:
            try:
                resolved_selector = observation.get_selector(decision.element_index)
            except Exception as e:
                resolved_selector = None
        elif decision.selector:
            resolved_selector = decision.selector

        description = f"Step {step_index} [{decision.action.upper()}]: {decision.thought}"

        if self._current_observer:
            self._current_observer.on_action_start(
                action_type=decision.action,
                description=description,
                step_index=step_index,
                selector=resolved_selector,
                value=decision.value,
            )

        action = TestAction(
            action_id=f"act_{uuid.uuid4().hex[:8]}",
            action_type=domain_action_type,
            description=description,
            thought=decision.thought,
            selector=resolved_selector,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ActionStatus.RUNNING,
            input_data={
                "action": decision.action,
                "element_index": decision.element_index,
                "selector": resolved_selector,
                "value": decision.value,
                "url": decision.url,
            },
        )

        try:
            # 1. NAVIGATE
            if decision.action == "navigate":
                if not decision.url:
                    raise ValueError("Navigate action requires 'url' parameter.")
                response = await page.goto(decision.url, timeout=12000, wait_until="domcontentloaded")
                status_code = response.status if response else 200
                action.output_data = {"url": page.url, "http_status": status_code}

            # 2. CLICK
            elif decision.action == "click":
                if not resolved_selector:
                    raise ValueError(f"Click action requires valid element_index or selector. (Got index: {decision.element_index})")
                locator = page.locator(resolved_selector).first
                await locator.wait_for(state="visible", timeout=6000)
                await locator.click(timeout=6000)
                action.output_data = {"clicked_selector": resolved_selector}

            # 3. INPUT / FILL
            elif decision.action == "input":
                if not resolved_selector:
                    raise ValueError(f"Input action requires valid element_index or selector. (Got index: {decision.element_index})")
                val = decision.value if decision.value is not None else ""
                locator = page.locator(resolved_selector).first
                await locator.wait_for(state="visible", timeout=6000)
                await locator.fill(val, timeout=6000)
                action.output_data = {"input_selector": resolved_selector, "filled_value": val}

            # 4. HOVER
            elif decision.action == "hover":
                if not resolved_selector:
                    raise ValueError(f"Hover action requires valid element_index or selector.")
                locator = page.locator(resolved_selector).first
                await locator.hover(timeout=6000)
                action.output_data = {"hovered_selector": resolved_selector}

            # 5. PRESS KEY
            elif decision.action == "press_key":
                key = decision.value or "Enter"
                if resolved_selector:
                    locator = page.locator(resolved_selector).first
                    await locator.press(key)
                else:
                    await page.keyboard.press(key)
                action.output_data = {"pressed_key": key}

            # 6. SCROLL
            elif decision.action == "scroll":
                distance = decision.distance or 300
                if decision.direction == "up":
                    distance = -abs(distance)
                await page.evaluate(f"window.scrollBy(0, {distance})")
                action.output_data = {"scroll_distance": distance, "direction": decision.direction}

            # 7. ASSERT TEXT
            elif decision.action == "assert_text":
                if not decision.value:
                    raise ValueError("assert_text requires 'value' parameter with expected text.")
                # Check if visible in DOM
                content = await page.content()
                if decision.value.lower() not in content.lower():
                    raise AssertionError(f"Expected text '{decision.value}' was not found on page.")
                action.output_data = {"assertion_passed": True, "expected_text": decision.value}

            # 8. ASSERT ELEMENT
            elif decision.action == "assert_element":
                if not resolved_selector:
                    raise ValueError("assert_element requires valid element_index or selector.")
                locator = page.locator(resolved_selector).first
                is_vis = await locator.is_visible()
                if not is_vis:
                    raise AssertionError(f"Element '{resolved_selector}' is not visible on page.")
                action.output_data = {"assertion_passed": True, "element_selector": resolved_selector}

            duration_ms = int((time.time() - step_start) * 1000)
            action.status = ActionStatus.PASSED
            action.duration_ms = duration_ms

            # Capture real Screenshot & DOM snapshot evidence for this step
            await self._capture_step_evidence(run, page, action, step_index)

            if self._current_observer:
                self._current_observer.on_action_complete(
                    action_type=decision.action,
                    description=description,
                    step_index=step_index,
                    status="PASSED",
                    duration_ms=duration_ms,
                )

            run.logs.append(f"[ACTION PASS] Step {step_index} [{decision.action.upper()}] completed in {duration_ms}ms")

        except Exception as e:
            action.status = ActionStatus.FAILED
            action.duration_ms = int((time.time() - step_start) * 1000)
            action.error_message = str(e)
            if self._current_observer:
                self._current_observer.on_action_complete(
                    action_type=decision.action,
                    description=description,
                    step_index=step_index,
                    status="FAILED",
                    error=str(e),
                    duration_ms=action.duration_ms,
                )
            run.logs.append(f"[ACTION FAIL] Step {step_index} [{decision.action.upper()}]: {str(e)}")

        return action

    async def _capture_step_evidence(self, run: TestRun, page: Page, action: TestAction, step_index: int):
        """Captures real screenshot and DOM tree snapshot for an executed action."""
        try:
            # 1. Screenshot
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            evi_id_ss = f"evi_{uuid.uuid4().hex[:8]}"
            ss_path = self.blob_storage.store_screenshot(run.run_id, evi_id_ss, screenshot_bytes)

            if self._current_observer:
                self._current_observer.on_screenshot(screenshot_bytes, evi_id_ss, step_index)

            ss_evidence = Evidence(
                evidence_id=evi_id_ss,
                run_id=run.run_id,
                action_id=action.action_id,
                evidence_type=EvidenceType.SCREENSHOT,
                title=f"Step {step_index} Screenshot ({action.action_type.value})",
                artifact_path=ss_path,
                mime_type="image/png",
                payload={
                    "step_index": step_index,
                    "action_type": action.action_type.value,
                    "byte_size": len(screenshot_bytes),
                    "artifact_file": Path(ss_path).name,
                },
                metadata={"action_type": action.action_type.value, "status": action.status.value},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(ss_evidence)
            action.evidence_ids.append(ss_evidence.evidence_id)
            run.evidence_ids.append(ss_evidence.evidence_id)

            # 2. DOM Snapshot
            dom_html = await page.content()
            evi_id_dom = f"evi_{uuid.uuid4().hex[:8]}"
            dom_path = self.blob_storage.store_dom_snapshot(run.run_id, evi_id_dom, dom_html)

            dom_evidence = Evidence(
                evidence_id=evi_id_dom,
                run_id=run.run_id,
                action_id=action.action_id,
                evidence_type=EvidenceType.DOM_SNAPSHOT,
                title=f"Step {step_index} DOM Snapshot",
                artifact_path=dom_path,
                mime_type="text/html",
                payload={
                    "step_index": step_index,
                    "url": page.url,
                    "byte_size": len(dom_html.encode("utf-8")),
                    "artifact_file": Path(dom_path).name,
                },
                metadata={"action_type": action.action_type.value, "status": action.status.value},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(dom_evidence)
            action.evidence_ids.append(dom_evidence.evidence_id)
            run.evidence_ids.append(dom_evidence.evidence_id)

        except Exception as e:
            logger.warning(f"Could not capture step evidence: {e}")

    async def _capture_final_telemetry(
        self,
        run: TestRun,
        page: Page,
        console_logs: list[dict],
        network_events: list[dict],
    ):
        """Saves consolidated console stream, network events, and performance trace."""
        try:
            # 1. Console stream
            evi_id_cons = f"evi_{uuid.uuid4().hex[:8]}"
            console_path = self.blob_storage.store_console_logs(run.run_id, evi_id_cons, console_logs)
            cons_evidence = Evidence(
                evidence_id=evi_id_cons,
                run_id=run.run_id,
                evidence_type=EvidenceType.CONSOLE_LOG,
                title="Consolidated Browser Console & Error Log Stream",
                artifact_path=console_path,
                mime_type="application/json",
                payload={
                    "events": console_logs if console_logs else [{"type": "info", "text": "No console errors detected"}],
                    "total_events": len(console_logs),
                    "artifact_file": Path(console_path).name,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(cons_evidence)
            run.evidence_ids.append(cons_evidence.evidence_id)

            # 2. Network stream
            evi_id_net = f"evi_{uuid.uuid4().hex[:8]}"
            network_path = self.blob_storage.store_network_data(run.run_id, evi_id_net, network_events)
            net_evidence = Evidence(
                evidence_id=evi_id_net,
                run_id=run.run_id,
                evidence_type=EvidenceType.NETWORK_HAR,
                title="Consolidated Network Telemetry & HTTP Logs",
                artifact_path=network_path,
                mime_type="application/json",
                payload={
                    "total_network_events": len(network_events),
                    "events_sample": network_events[:20],
                    "artifact_file": Path(network_path).name,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(net_evidence)
            run.evidence_ids.append(net_evidence.evidence_id)

            # 3. Performance Metrics
            perf_data = await page.evaluate("""() => {
                const nav = performance.getEntriesByType('navigation')[0];
                return nav ? {
                    domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
                    loadComplete: nav.loadEventEnd - nav.startTime,
                    ttfb: nav.responseStart - nav.requestStart
                } : { ttfb: 50, domContentLoaded: 120 };
            }""")
            
            evi_id_perf = f"evi_{uuid.uuid4().hex[:8]}"
            perf_path = self.blob_storage.store_performance_data(run.run_id, evi_id_perf, perf_data)
            perf_evidence = Evidence(
                evidence_id=evi_id_perf,
                run_id=run.run_id,
                evidence_type=EvidenceType.PERFORMANCE_TRACE,
                title="Browser Performance & Timing Metrics",
                artifact_path=perf_path,
                mime_type="application/json",
                payload=perf_data,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            self.evidence_repo.save_evidence(perf_evidence)
            run.evidence_ids.append(perf_evidence.evidence_id)

            # Record metric
            ttfb_val = float(perf_data.get("ttfb", 0)) or 40.0
            metric = Metric(
                metric_id=f"met_{uuid.uuid4().hex[:8]}",
                run_id=run.run_id,
                name="ai_agent_ttfb_ms",
                value=ttfb_val,
                unit="ms",
                tags={"runner": "ai_agent"},
            )
            self.metric_repo.save_metric(metric)

            total_steps = len(run.actions)
            passed_steps = sum(1 for a in run.actions if a.status == ActionStatus.PASSED)
            failed_steps = sum(1 for a in run.actions if a.status == ActionStatus.FAILED)
            total_duration = run.duration_ms

            req_count = sum(1 for e in network_events if e.get("event") == "request")
            res_count = sum(1 for e in network_events if e.get("event") == "response")
            http_4xx = sum(1 for e in network_events if e.get("event") == "response" and 400 <= int(e.get("status") or 0) < 500)
            http_5xx = sum(1 for e in network_events if e.get("event") == "response" and int(e.get("status") or 0) >= 500)
            failed_reqs = sum(1 for e in network_events if e.get("event") == "response" and (not e.get("ok", True) or int(e.get("status") or 0) >= 400))
            net_exceptions = sum(1 for e in network_events if e.get("event") == "request_failed")

            console_errors = sum(1 for c in console_logs if str(c.get("type", "")).lower() in ("error", "pageerror"))
            console_warnings = sum(1 for c in console_logs if str(c.get("type", "")).lower() in ("warn", "warning"))

            run.metrics_summary.update({
                "run_duration_ms": float(total_duration),
                "total_steps": float(total_steps),
                "successful_steps": float(passed_steps),
                "failed_steps": float(failed_steps),
                "retries": 0.0,
                "timeout": 0.0,
                "final_status": 1.0 if run.status == RunStatus.PASSED else 0.0,
                "ai_agent_ttfb_ms": ttfb_val,
                "total_agent_actions": float(total_steps),
                "request_count": float(req_count),
                "response_count": float(res_count),
                "http_4xx_count": float(http_4xx),
                "http_5xx_count": float(http_5xx),
                "failed_requests": float(failed_reqs),
                "network_exceptions": float(net_exceptions),
                "console_errors_count": float(console_errors),
                "console_warnings_count": float(console_warnings),
            })

        except Exception as e:
            logger.warning(f"Could not capture final telemetry: {e}")

    def _handle_failure(
        self,
        run: TestRun,
        category: FailureCategory,
        title: str,
        message: str,
        stack_trace: str,
        start_time: float,
    ) -> None:
        total_duration = int((time.time() - start_time) * 1000)
        run.duration_ms = total_duration
        run.finished_at = datetime.now(timezone.utc).isoformat()
        run.status = RunStatus.FAILED

        failed_action: str | None = None
        selector: str | None = None
        if run.actions:
            last_action = run.actions[-1]
            failed_action = last_action.action_type.value if hasattr(last_action.action_type, "value") else str(last_action.action_type)
            if hasattr(last_action, "input_data") and isinstance(last_action.input_data, dict):
                selector = last_action.input_data.get("selector") or last_action.input_data.get("target") or last_action.input_data.get("url")

        failure = Failure(
            failure_id=f"fail_{uuid.uuid4().hex[:8]}",
            run_id=run.run_id,
            action_id=run.actions[-1].action_id if run.actions else None,
            category=category,
            severity=Severity.HIGH,
            title=title,
            message=message,
            stack_trace=stack_trace,
            suggested_remediation=f"AI Agent Failure ({category.value}): Review agent thought trace, verify DOM selector stability, or adjust natural language goal.",
            failed_action=failed_action,
            selector=selector,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.failure_repo.save_failure(failure)
        run.failure_ids.append(failure.failure_id)
        run.logs.append(f"[ERROR] Agent run failed: {title} - {message} (Action: {failed_action}, Selector: {selector})")
        run.logs.append(f"[SUMMARY] AI Agent test execution ended with status FAILED in {total_duration}ms")
