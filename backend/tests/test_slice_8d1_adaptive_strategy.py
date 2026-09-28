"""
Slice 8D.1 — Application-Adaptive Autonomous Testing Strategy Test Suite

Validates:
1. Application Archetype Derivation across diverse application domains.
2. Strategy Differentiation: App A -> Strategy A; App B -> Strategy B.
3. Behavioral Contract Integration from Slice 8C context.
4. Historical Failure & Risk Profiling.
5. Dynamic Runtime Adaptation (Error recovery, Blocked workflows, Budget pressure, Workflow completion).
6. Invariant Verification: Strategy is a planning artifact; runtime observation supersedes assumptions.
7. Structured telemetry: No private Chain-of-Thought leakage.
8. Live session bus integration: STRATEGY_PLANNED and STRATEGY_ADAPTED events.
9. AIAgentTestRunner execution with adaptive strategy guidance.
10. Live Testing Strategy API endpoint.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.app.models.enums import TargetType, TestMode, ActionStatus, RunnerType, ExecutionSource, FailureCategory
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_run import TestRun, TestRunCreate
from backend.app.models.test_action import TestAction
from backend.app.models.failure import Failure
from backend.app.models.dogfooding_context import DogfoodingRunContext
from backend.app.agents.dom_extractor import DOMObservation, ExtractedElement
from backend.app.agents.ollama_agent import OllamaReasoner, AgentDecision
from backend.app.dogfooding.strategy_models import (
    ApplicationArchetype,
    StrategyMode,
    WorkflowPriorityStatus,
    PrioritizedWorkflow,
    StrategyAdaptationTrigger,
    TestingStrategy,
)
from backend.app.dogfooding.strategy_engine import AdaptiveStrategyEngine
from backend.app.dogfooding.live_events import LiveEventType, LiveEvent
from backend.app.dogfooding.live_session_bus import LiveSessionEventBus
from backend.app.dogfooding.runner_observer import LiveRunnerObserver
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.execution.ai_agent_runner import AIAgentTestRunner
from fastapi.testclient import TestClient
from backend.app.main import app


# -------------------------------------------------------------------------
# 1. Archetype Derivation Tests
# -------------------------------------------------------------------------

def test_01_archetype_derivation_ai_application():
    target = ApplicationTarget(
        target_id="tgt_qgen",
        application_id="app_question_generator",
        application_type="ai_eval_agent",
        name="VM Copy Question Generator",
        base_url="http://localhost:3000",
        description="AI-driven mathematical question generator using LLM inference",
    )
    archetype = AdaptiveStrategyEngine.derive_archetype(
        target=target,
        goal="Generate questions and test 4-option contract",
    )
    assert archetype == ApplicationArchetype.AI_APPLICATION


def test_02_archetype_derivation_data_dashboard():
    target = ApplicationTarget(
        target_id="tgt_dash",
        application_id="app_telemetry",
        application_type="web_app",
        name="System Telemetry & Metrics Dashboard",
        base_url="http://localhost:3000/dashboard",
        description="Interactive grid displaying platform performance analytics and telemetry metrics",
    )
    archetype = AdaptiveStrategyEngine.derive_archetype(
        target=target,
        goal="Verify dashboard metrics and table sorting",
    )
    assert archetype == ApplicationArchetype.DATA_DASHBOARD


def test_03_archetype_derivation_form_workflow():
    target = ApplicationTarget(
        target_id="tgt_wizard",
        application_id="app_registration",
        name="Candidate Onboarding Wizard",
        base_url="http://localhost:3000/onboard",
        description="Multi-step registration form and questionnaire",
    )
    archetype = AdaptiveStrategyEngine.derive_archetype(
        target=target,
        goal="Submit candidate onboarding form",
    )
    assert archetype == ApplicationArchetype.FORM_WORKFLOW


def test_04_archetype_derivation_ecommerce():
    target = ApplicationTarget(
        target_id="tgt_store",
        application_id="app_catalog",
        name="Cloud Equipment Store",
        base_url="http://localhost:3000/shop",
        description="Online storefront with product catalog and cart checkout",
    )
    archetype = AdaptiveStrategyEngine.derive_archetype(
        target=target,
        goal="Add items to cart and proceed to checkout",
    )
    assert archetype == ApplicationArchetype.E_COMMERCE


def test_05_archetype_derivation_generic_web():
    target = ApplicationTarget(
        target_id="tgt_generic",
        application_id="app_landing",
        name="Documentation Site",
        base_url="http://localhost:3000/docs",
        description="Static docs layout",
    )
    archetype = AdaptiveStrategyEngine.derive_archetype(
        target=target,
        goal="Explore documentation navigation",
    )
    assert archetype == ApplicationArchetype.GENERIC_WEB


# -------------------------------------------------------------------------
# 2. Strategy Differentiation Invariant: App A -> Strat A; App B -> Strat B
# -------------------------------------------------------------------------

def test_06_strategy_differentiation_app_a_vs_app_b():
    target_a = ApplicationTarget(
        target_id="tgt_ai_app",
        application_id="ai_question_app",
        name="AI Question Generator",
        base_url="http://localhost:3000",
    )
    target_b = ApplicationTarget(
        target_id="tgt_ecommerce_app",
        application_id="ecommerce_app",
        name="E-Commerce Storefront",
        base_url="http://localhost:3000/shop",
    )

    strat_a = AdaptiveStrategyEngine.build_strategy(
        run_id="run_a",
        target=target_a,
        goal="Test question generation",
    )
    strat_b = AdaptiveStrategyEngine.build_strategy(
        run_id="run_b",
        target=target_b,
        goal="Test product cart and checkout",
    )

    # Invariant: Different applications produce fundamentally different workflows
    assert strat_a.application_archetype == ApplicationArchetype.AI_APPLICATION
    assert strat_b.application_archetype == ApplicationArchetype.E_COMMERCE

    names_a = [w.name for w in strat_a.prioritized_workflows]
    names_b = [w.name for w in strat_b.prioritized_workflows]
    assert names_a != names_b

    # Exploration policies also differ
    assert strat_a.exploration_policy.assertion_density == "INTENSIVE"
    assert strat_b.exploration_policy.assertion_density == "BALANCED"


# -------------------------------------------------------------------------
# 3. Behavioral Contracts & Historical Risk Profiling
# -------------------------------------------------------------------------

def test_07_behavioral_contracts_bound_to_strategy():
    target = ApplicationTarget(
        target_id="tgt_ai_contracts",
        name="AI Question Generator",
        base_url="http://localhost:3000",
    )
    context = DogfoodingRunContext(
        run_id="run_contract_test",
        evaluation_context_id="eval_ctx_001",
        context_hash="hash_abc123",
        application_id="app_qgen",
        feature_id="feat_gen",
        prompt_id="prompt_qgen",
        prompt_version=1,
        model="qwen2.5-coder:7b-instruct",
        behavioral_contract_ids=["contract_exclusive_ca", "contract_four_options"],
        ai_feature_detected=True,
    )

    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_contract_test",
        target=target,
        goal="Verify behavioral contracts",
        context=context,
    )

    assert strategy.strategy_mode == StrategyMode.CONTRACT_VERIFICATION
    assert strategy.behavioral_contract_ids == ["contract_exclusive_ca", "contract_four_options"]

    # Workflow verifying contracts must have elevated priority
    contract_wf = next(w for w in strategy.prioritized_workflows if "Contract" in w.name)
    assert contract_wf.priority >= 0.95
    assert contract_wf.associated_contract_ids == ["contract_exclusive_ca", "contract_four_options"]


def test_08_historical_failures_populate_risk_areas():
    target = ApplicationTarget(
        target_id="tgt_fragile",
        name="Fragile Application",
        base_url="http://localhost:3000",
    )
    past_failures = [
        Failure(
            failure_id="fail_1",
            run_id="run_past_1",
            category=FailureCategory.EXECUTION_TIMEOUT,
            title="Timeout Failure",
            failed_action="button_generate_click",
            message="Timeout waiting for generate selector",
        ),
        Failure(
            failure_id="fail_2",
            run_id="run_past_2",
            category=FailureCategory.ASSERTION_FAILED,
            title="Option Mismatch Failure",
            selector="options_validation",
            message="Options count mismatch",
        ),
    ]

    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_risk_test",
        target=target,
        goal="Test with historical risk awareness",
        historical_failures=past_failures,
    )

    assert "button_generate_click" in strategy.risk_areas
    assert "options_validation" in strategy.risk_areas
    assert strategy.historical_failure_count == 2
    assert strategy.strategy_mode == StrategyMode.REGRESSION_PROBING


# -------------------------------------------------------------------------
# 4. Dynamic Runtime Adaptation Tests
# -------------------------------------------------------------------------

def test_09_runtime_adaptation_on_action_failure():
    target = ApplicationTarget(
        target_id="tgt_adapt_fail",
        name="AI App",
        base_url="http://localhost:3000",
    )
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_adapt_1",
        target=target,
        goal="Test AI Generation",
    )

    initial_active_id = strategy.active_workflow_id
    assert initial_active_id is not None

    failed_action = TestAction(
        action_id="act_fail_1",
        action_type="CLICK",
        description="Click input parameter",
        status=ActionStatus.FAILED,
        error_message="Element not found: #topic",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    obs = DOMObservation(url="http://localhost:3000", title="Test", elements=[], text_summary="")

    # Attempt 1
    strategy, event1 = AdaptiveStrategyEngine.adapt_strategy(
        strategy=strategy,
        step_number=1,
        max_steps=10,
        observation=obs,
        last_action=failed_action,
    )
    assert event1 is None  # Under error tolerance (2)

    # Attempt 2: Reaches error tolerance -> triggers WORKFLOW_BLOCKED
    strategy, event2 = AdaptiveStrategyEngine.adapt_strategy(
        strategy=strategy,
        step_number=2,
        max_steps=10,
        observation=obs,
        last_action=failed_action,
    )
    assert event2 is not None
    assert event2.trigger == StrategyAdaptationTrigger.WORKFLOW_BLOCKED
    assert event2.adaptation_type == "SKIP_BLOCKED"
    assert strategy.active_workflow_id != initial_active_id

    # Previous workflow marked as BLOCKED
    blocked_wf = next(w for w in strategy.prioritized_workflows if w.workflow_id == initial_active_id)
    assert blocked_wf.status == WorkflowPriorityStatus.BLOCKED


def test_10_runtime_adaptation_on_budget_pressure():
    target = ApplicationTarget(
        target_id="tgt_budget_test",
        name="AI App",
        base_url="http://localhost:3000",
    )
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_budget_1",
        target=target,
        goal="Test AI Generation",
    )

    obs = DOMObservation(url="http://localhost:3000", title="Test", elements=[], text_summary="")
    action = TestAction(
        action_id="act_pass_1",
        action_type="CUSTOM",
        description="Routine step",
        status=ActionStatus.PASSED,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # At step 8 of 10 (80% of budget)
    strategy, event = AdaptiveStrategyEngine.adapt_strategy(
        strategy=strategy,
        step_number=8,
        max_steps=10,
        observation=obs,
        last_action=action,
    )

    assert event is not None
    assert event.trigger == StrategyAdaptationTrigger.BUDGET_PRESSURE
    assert event.adaptation_type == "PRUNE_BUDGET"

    # Low priority workflows pruned
    abandoned = [w for w in strategy.prioritized_workflows if w.status == WorkflowPriorityStatus.ABANDONED]
    assert len(abandoned) > 0


def test_11_runtime_adaptation_on_workflow_completion():
    target = ApplicationTarget(
        target_id="tgt_complete_test",
        name="AI App",
        base_url="http://localhost:3000",
    )
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_comp_1",
        target=target,
        goal="Test AI Generation",
    )

    first_wf = strategy.get_active_workflow()
    assert first_wf is not None
    initial_id = first_wf.workflow_id

    # Passed action matching the active workflow
    passed_action = TestAction(
        action_id="act_pass_input",
        action_type="INPUT",
        description="Typed topic parameter into input field",
        thought="Inputs are populated",
        status=ActionStatus.PASSED,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    obs = DOMObservation(url="http://localhost:3000", title="Test", elements=[], text_summary="")

    strategy, event = AdaptiveStrategyEngine.adapt_strategy(
        strategy=strategy,
        step_number=1,
        max_steps=10,
        observation=obs,
        last_action=passed_action,
    )

    assert event is not None
    assert event.trigger == StrategyAdaptationTrigger.EARLY_COMPLETION
    assert event.adaptation_type == "ADVANCE_VERIFIED"
    assert strategy.active_workflow_id != initial_id

    completed_wf = next(w for w in strategy.prioritized_workflows if w.workflow_id == initial_id)
    assert completed_wf.status == WorkflowPriorityStatus.VERIFIED


# -------------------------------------------------------------------------
# 5. Telemetry & Invariants
# -------------------------------------------------------------------------

def test_12_strategy_guidance_formatting():
    target = ApplicationTarget(
        target_id="tgt_guidance",
        name="AI App",
        base_url="http://localhost:3000",
    )
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_guidance_1",
        target=target,
        goal="Verify AI Question Generator",
    )

    guidance = AdaptiveStrategyEngine.format_strategy_guidance(
        strategy=strategy,
        current_step=1,
        max_steps=10,
    )

    assert "APPLICATION-ADAPTIVE TESTING STRATEGY" in guidance
    assert "AI_APPLICATION" in guidance
    assert "Active Workflow:" in guidance
    # Must NOT contain private reasoning markers
    assert "chain_of_thought" not in guidance.lower()
    assert "hidden_cot" not in guidance.lower()


def test_13_strategy_is_planning_artifact_not_dogma():
    """
    Critical Invariant:
    The strategy is a planning artifact, not authoritative evidence.
    Observed runtime behavior always takes precedence over declared assumptions.
    """
    target = ApplicationTarget(
        target_id="tgt_invariant",
        name="Hypothetical Form App",
        base_url="http://localhost:3000",
    )
    strategy = AdaptiveStrategyEngine.build_strategy(
        run_id="run_inv",
        target=target,
        goal="Test form submission",
    )
    # Strategy declares a workflow
    active_wf = strategy.get_active_workflow()
    assert active_wf is not None

    # Observed runtime DOM shows no matching input elements (e.g. page is a 404 or maintenance page)
    obs = DOMObservation(
        url="http://localhost:3000/maintenance",
        title="503 Service Unavailable",
        elements=[],
        text_summary="Maintenance in progress",
    )
    # The observer sees 0 interactive elements
    assert len(obs.elements) == 0

    # Failing action confirms observed state supersedes declared strategy
    failing_action = TestAction(
        action_id="act_inv_1",
        action_type="NAVIGATE",
        description="Navigated to target page",
        status=ActionStatus.FAILED,
        error_message="HTTP 503 Maintenance",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    strategy, _ = AdaptiveStrategyEngine.adapt_strategy(
        strategy=strategy,
        step_number=1,
        max_steps=10,
        observation=obs,
        last_action=failing_action,
    )
    # Strategy recorded the runtime failure rather than dogmatically pretending the form exists
    assert active_wf.attempts == 1


# -------------------------------------------------------------------------
# 6. Live Session Event Bus & Observer Integration
# -------------------------------------------------------------------------

def test_14_live_event_bus_strategy_events():
    bus = LiveSessionEventBus()
    session = bus.create_session(
        run_id="run_bus_strat_test",
        target_id="tgt_bus_test",
        application_id="app_test",
        total_steps=10,
    )

    strat_data = {
        "strategy_id": "strat_123",
        "application_archetype": "AI_APPLICATION",
        "strategy_mode": "CONTRACT_VERIFICATION",
    }
    bus.publish(
        session_id=session.session_id,
        event_type=LiveEventType.STRATEGY_PLANNED,
        payload=strat_data,
    )

    adapt_data = {
        "adaptation_id": "adapt_456",
        "trigger": "WORKFLOW_BLOCKED",
        "reason": "Button disabled",
    }
    bus.publish(
        session_id=session.session_id,
        event_type=LiveEventType.STRATEGY_ADAPTED,
        payload=adapt_data,
    )

    events = bus.get_events(session.session_id)
    assert len(events) == 3
    assert events[1].event_type == LiveEventType.STRATEGY_PLANNED
    assert events[2].event_type == LiveEventType.STRATEGY_ADAPTED
    assert events[1].sequence_number == 2
    assert events[2].sequence_number == 3


def test_15_runner_observer_strategy_hooks():
    bus = LiveSessionEventBus()
    with patch("backend.app.dogfooding.runner_observer.live_event_bus", bus):
        run = TestRun(
            run_id="run_obs_strat_test",
            application_id="app_obs_test",
            test_mode=TestMode.EXPLORATORY_DOGFOODING,
            runner_type=RunnerType.AI_AGENT,
        )
        observer = LiveRunnerObserver.for_run(run)

        # Emit strategy planned with forbidden keys to test sanitization
        observer.on_strategy_planned({
            "archetype": "AI_APPLICATION",
            "chain_of_thought": "SECRET_THOUGHTS",
            "prompt_template": "INTERNAL_PROMPT",
        })

        observer.on_strategy_adapted({
            "reason": "Recovered from error",
            "reasoning_content": "PRIVATE_COT",
        })

        events = bus.get_events(observer.session_id)
        assert len(events) == 3

        # Sanitization check
        assert "chain_of_thought" not in events[1].payload
        assert "prompt_template" not in events[1].payload
        assert events[1].payload["archetype"] == "AI_APPLICATION"

        assert "reasoning_content" not in events[2].payload
        assert events[2].payload["reason"] == "Recovered from error"


# -------------------------------------------------------------------------
# 7. AIAgentTestRunner End-to-End Execution with Adaptive Strategy
# -------------------------------------------------------------------------

def test_16_ai_agent_runner_executes_with_adaptive_strategy(tmp_path):
    db_path = str(tmp_path / "test_strategy_runner.db")
    repo = SQLiteRepository(db_path=db_path)
    storage = LocalEvidenceBlobStorage(base_dir=tmp_path / "artifacts")

    html_file = tmp_path / "adaptive_target.html"
    html_file.write_text(
        "<!DOCTYPE html><html><body><h1>Adaptive App</h1><button id='action-btn' onclick='document.body.innerHTML=\"<h1>Done!</h1>\";'>Click Me</button></body></html>",
        encoding="utf-8"
    )

    target = ApplicationTarget(
        target_id="tgt_strat_runner",
        application_id="app_strat_runner",
        name="Local Adaptive Target",
        base_url=f"file:///{html_file.as_posix()}",
    )
    repo.create_target(target)

    run = TestRun(
        run_id="run_strat_exec_1",
        application_id=target.target_id,
        test_mode=TestMode.EXPLORATORY_DOGFOODING,
        runner_type=RunnerType.AI_AGENT,
        natural_language_goal="Click action button and finish",
    )
    repo.create_run(run)

    # Mock reasoner to return click on step 1, finish_pass on step 2
    mock_reasoner = MagicMock(spec=OllamaReasoner)
    mock_reasoner.model = "qwen2.5-coder:7b-instruct"
    mock_reasoner.decide_next_action.side_effect = [
        AgentDecision(thought="Clicking button based on strategy", action="click", selector="#action-btn"),
        AgentDecision(thought="Goal completed", action="finish_pass", reason="Successfully finished"),
    ]

    runner = AIAgentTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=storage,
        reasoner=mock_reasoner,
    )

    options = TestRunCreate(
        application_id=target.target_id,
        runner_type=RunnerType.AI_AGENT,
        test_mode=TestMode.EXPLORATORY_DOGFOODING,
        max_agent_steps=5,
    )

    executed_run = asyncio.run(runner.execute(run, target, options))

    # Verify run completed
    assert executed_run.status.value == "PASSED"

    # Verify strategy was attached to run metadata
    assert "testing_strategy" in executed_run.metadata
    strat_meta = executed_run.metadata["testing_strategy"]
    assert "strategy_id" in strat_meta
    assert "application_archetype" in strat_meta
    assert "total_workflows" in strat_meta

    # Verify strategy guidance was passed to reasoner
    assert mock_reasoner.decide_next_action.call_count >= 1
    call_kwargs = mock_reasoner.decide_next_action.call_args_list[0].kwargs
    assert "strategy_guidance" in call_kwargs
    assert "APPLICATION-ADAPTIVE TESTING STRATEGY" in call_kwargs["strategy_guidance"]


# -------------------------------------------------------------------------
# 8. API Endpoint Test
# -------------------------------------------------------------------------

def test_17_api_get_session_strategy():
    from backend.app.dogfooding.live_session_bus import live_event_bus
    client = TestClient(app)

    session = live_event_bus.create_session(
        run_id="run_api_strat_test",
        target_id="tgt_api_strat",
        application_id="app_api_strat",
        total_steps=10,
    )

    live_event_bus.publish(
        session_id=session.session_id,
        event_type=LiveEventType.STRATEGY_PLANNED,
        payload={
            "strategy_id": "strat_api_999",
            "application_archetype": "AI_APPLICATION",
            "strategy_mode": "CONTRACT_VERIFICATION",
            "active_workflow": {"name": "Verify contracts"},
        },
    )

    resp = client.get(f"/api/v1/live/sessions/{session.session_id}/strategy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_id"] == "strat_api_999"
    assert data["application_archetype"] == "AI_APPLICATION"
