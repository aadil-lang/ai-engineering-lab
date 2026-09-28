"""
Slice 8D.1 — Application-Adaptive Autonomous Testing Strategy Engine

Derives and dynamically adapts testing strategies from application context,
capabilities, workflows, behavioral contracts, historical reliability data,
and real-time runtime observations.

Guiding Invariants:
1. Strategy is a planning artifact, not authoritative evidence.
2. Observed runtime behavior always takes precedence over declared assumptions.
3. Application A -> Strategy A; Application B -> Strategy B; Application C -> Strategy C.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import uuid
import logging

from backend.app.models.target import ApplicationTarget
from backend.app.models.enums import TestMode, ActionStatus
from backend.app.models.dogfooding_context import DogfoodingRunContext
from backend.app.models.failure import Failure
from backend.app.models.test_action import TestAction
from backend.app.agents.dom_extractor import DOMObservation
from backend.app.dogfooding.strategy_models import (
    ApplicationArchetype,
    StrategyMode,
    WorkflowPriorityStatus,
    PrioritizedWorkflow,
    ExplorationPolicy,
    StrategyAdaptationTrigger,
    StrategyAdaptationEvent,
    TestingStrategy,
)

logger = logging.getLogger("ai_qa_platform.strategy_engine")


class AdaptiveStrategyEngine:
    """
    Constructs and adapts testing strategies tailored to the target application.
    """

    @staticmethod
    def derive_archetype(
        target: ApplicationTarget,
        context: Optional[DogfoodingRunContext] = None,
        goal: str = "",
    ) -> ApplicationArchetype:
        """
        Infers the application archetype from target metadata, context, and goal.
        """
        text_corpus = f"{target.name} {target.description} {target.application_type or ''} {target.base_url} {goal}".lower()
        if context:
            text_corpus += f" {context.application_id} {context.feature_id} {context.model} {context.prompt_id}".lower()
            if context.ai_feature_detected:
                return ApplicationArchetype.AI_APPLICATION

        import re
        tokens = set(re.findall(r'[a-z0-9_-]+', text_corpus.lower()))

        # AI application heuristics
        ai_tokens = {
            "ai", "llm", "generator", "eval_agent",
            "prompt", "chat", "assistant", "qwen", "completion", "agent"
        }
        if any(tok in tokens for tok in ai_tokens) or "question generator" in text_corpus or "generate" in tokens:
            return ApplicationArchetype.AI_APPLICATION

        # Form / Wizard heuristics
        form_tokens = {"form", "wizard", "survey", "registration", "signup", "apply", "questionnaire", "onboarding"}
        if any(tok in tokens for tok in form_tokens):
            return ApplicationArchetype.FORM_WORKFLOW

        # Dashboard / Analytics heuristics
        dashboard_tokens = {"dashboard", "metrics", "telemetry", "analytics", "stats", "grid"}
        if any(tok in tokens for tok in dashboard_tokens):
            return ApplicationArchetype.DATA_DASHBOARD

        # E-Commerce heuristics
        ecommerce_tokens = {"shop", "store", "product", "cart", "checkout", "catalog", "ecommerce"}
        if any(tok in tokens for tok in ecommerce_tokens):
            return ApplicationArchetype.E_COMMERCE

        # Content Management heuristics
        cms_tokens = {"cms", "blog", "article", "authoring"}
        if any(tok in tokens for tok in cms_tokens) or "content management" in text_corpus:
            return ApplicationArchetype.CONTENT_MANAGEMENT

        return ApplicationArchetype.GENERIC_WEB

    @staticmethod
    def derive_strategy_mode(
        test_mode: TestMode,
        has_contracts: bool = False,
        has_historical_failures: bool = False,
    ) -> StrategyMode:
        """Determines the appropriate strategy mode."""
        if has_contracts:
            return StrategyMode.CONTRACT_VERIFICATION
        if has_historical_failures:
            return StrategyMode.REGRESSION_PROBING
        if test_mode == TestMode.EXPLORATORY_DOGFOODING:
            return StrategyMode.EXPLORATORY_DISCOVERY
        if test_mode == TestMode.REGRESSION:
            return StrategyMode.REGRESSION_PROBING
        return StrategyMode.CRITICAL_PATH_WALKTHROUGH

    @classmethod
    def build_strategy(
        cls,
        run_id: str,
        target: ApplicationTarget,
        goal: str,
        test_mode: TestMode = TestMode.EXPLORATORY_DOGFOODING,
        context: Optional[DogfoodingRunContext] = None,
        historical_failures: Optional[List[Failure]] = None,
        retrieved_memories: Optional[List[Any]] = None,
    ) -> TestingStrategy:
        """
        Constructs a customized TestingStrategy for the given application.
        Integrates Slice 8E Engineering Memory to formulate testing hypotheses.
        """
        archetype = cls.derive_archetype(target=target, context=context, goal=goal)
        contract_ids = context.behavioral_contract_ids if context else []
        risk_areas: List[str] = []
        historical_failures = historical_failures or []
        retrieved_memories = retrieved_memories or []

        for f in historical_failures:
            if getattr(f, "category", None) and f.category.value not in risk_areas:
                risk_areas.append(f.category.value)
            step = getattr(f, "failed_action", None) or getattr(f, "selector", None)
            if step and step not in risk_areas:
                risk_areas.append(step)

        # Slice 8E: Process retrieved memories into testing hypotheses & risk areas
        mem_summaries: List[str] = []
        memory_probe_workflows: List[PrioritizedWorkflow] = []

        for item in retrieved_memories:
            # Handle MemorySearchResult or EngineeringMemory or dict
            mem_obj = getattr(item, "memory", item)
            m_type = getattr(mem_obj, "memory_type", None) or (mem_obj.get("memory_type") if isinstance(mem_obj, dict) else None)
            m_content = getattr(mem_obj, "content", None) or (mem_obj.get("content") if isinstance(mem_obj, dict) else str(mem_obj))
            m_type_val = getattr(m_type, "value", str(m_type)) if m_type else "UNKNOWN"
            mem_summaries.append(f"[{m_type_val}] {m_content[:80]}")

            if m_type_val in ("FAILURE_HISTORY", "REGRESSION_HISTORY"):
                risk_areas.append(f"Historical Failure Hypothesis: {m_content[:60]}")
                # Formulate a regression probe workflow hypothesis
                memory_probe_workflows.append(
                    PrioritizedWorkflow(
                        name=f"Historical Regression Probe: {m_content[:40]}",
                        description=f"Validate historical failure hypothesis: {m_content}",
                        archetype_affinity=archetype,
                        priority=0.92,
                        target_selectors=["button", "input", ".question-card"],
                        expected_state_change="Verify that previously observed failure does not recur",
                    )
                )

        mode = cls.derive_strategy_mode(
            test_mode=test_mode,
            has_contracts=len(contract_ids) > 0,
            has_historical_failures=len(historical_failures) > 0 or len(memory_probe_workflows) > 0,
        )

        # Build archetype-tailored workflows
        workflows = cls._build_workflows_for_archetype(
            archetype=archetype,
            target=target,
            goal=goal,
            contract_ids=contract_ids,
            risk_areas=risk_areas,
        )

        # Prepend or blend memory regression probes
        if memory_probe_workflows:
            workflows = memory_probe_workflows + workflows

        # Set default exploration policy tailored to archetype and risk
        policy = cls._build_exploration_policy(archetype=archetype, risk_areas=risk_areas)

        # Activate initial highest priority workflow
        active_wf_id = None
        if workflows:
            highest_wf = max(workflows, key=lambda w: w.priority)
            highest_wf.status = WorkflowPriorityStatus.IN_PROGRESS
            active_wf_id = highest_wf.workflow_id

        strategy = TestingStrategy(
            run_id=run_id,
            target_id=target.target_id,
            application_id=target.application_id,
            application_archetype=archetype,
            strategy_mode=mode,
            goal=goal,
            declared_context_hash=context.context_hash if context else None,
            behavioral_contract_ids=contract_ids,
            prioritized_workflows=workflows,
            active_workflow_id=active_wf_id,
            exploration_policy=policy,
            risk_areas=risk_areas,
            historical_failure_count=len(historical_failures),
            retrieved_memory_count=len(retrieved_memories),
            retrieved_memory_summaries=mem_summaries,
        )

        logger.info(
            f"[STRATEGY] Created strategy {strategy.strategy_id} for target {target.target_id} "
            f"(archetype: {archetype.value}, mode: {mode.value}, workflows: {len(workflows)}, memories: {len(retrieved_memories)})"
        )
        return strategy

    @classmethod
    def _build_workflows_for_archetype(
        cls,
        archetype: ApplicationArchetype,
        target: ApplicationTarget,
        goal: str,
        contract_ids: List[str],
        risk_areas: List[str],
    ) -> List[PrioritizedWorkflow]:
        """Generates domain-specific workflow priorities."""
        workflows: List[PrioritizedWorkflow] = []

        if archetype == ApplicationArchetype.AI_APPLICATION:
            workflows = [
                PrioritizedWorkflow(
                    name="Configure Generation Parameters & Inputs",
                    description="Enter prompt configurations, topics, difficulty levels, or parameters into form controls.",
                    archetype_affinity=archetype,
                    priority=0.90,
                    target_selectors=["input", "textarea", "select", "#topic", "#grade", "#difficulty"],
                    expected_state_change="Inputs populated and generate trigger enabled",
                ),
                PrioritizedWorkflow(
                    name="Trigger AI Generation & Observe Progress",
                    description="Dispatch generation action and monitor streaming or loading indicators.",
                    archetype_affinity=archetype,
                    priority=0.85,
                    target_selectors=["button:has-text('Generate')", "#generate-btn", "button[type='submit']"],
                    expected_state_change="Generation loading state visible followed by completion",
                ),
                PrioritizedWorkflow(
                    name="Verify Behavioral & Structural Output Contracts",
                    description="Inspect generated artifacts to verify mathematical and structural contracts (4 options, 1 CA, explanation).",
                    archetype_affinity=archetype,
                    priority=0.95 if contract_ids else 0.80,
                    target_selectors=[".question-card", ".options-grid", ".ca-tag", ".solution-box"],
                    expected_state_change="Output verified against contract rules",
                    associated_contract_ids=contract_ids,
                ),
                PrioritizedWorkflow(
                    name="Probe Boundary Inputs & Edge Cases",
                    description="Test empty topic prompts, rapid consecutive clicks, or extreme parameter configurations.",
                    archetype_affinity=archetype,
                    priority=0.60,
                    target_selectors=["input", "button"],
                    expected_state_change="Graceful error message or handled fallback",
                ),
            ]

        elif archetype == ApplicationArchetype.DATA_DASHBOARD:
            workflows = [
                PrioritizedWorkflow(
                    name="Verify Dashboard Metric Cards & Data Grid",
                    description="Verify that primary KPI summary cards and table rows render valid data without errors.",
                    archetype_affinity=archetype,
                    priority=0.90,
                    target_selectors=[".stat-card", "table", "tbody tr", ".metric-val"],
                    expected_state_change="Metrics rendered with non-zero or populated state",
                ),
                PrioritizedWorkflow(
                    name="Test Search, Filters & Sorting Controls",
                    description="Apply search query filters, category dropdowns, and column header sorts.",
                    archetype_affinity=archetype,
                    priority=0.80,
                    target_selectors=["input[type='search']", "select", "th[role='columnheader']"],
                    expected_state_change="Data grid updates matching filter criteria",
                ),
                PrioritizedWorkflow(
                    name="Inspect Detail Views & Modals",
                    description="Click on an individual row or metric to open drawer or modal inspection view.",
                    archetype_affinity=archetype,
                    priority=0.70,
                    target_selectors=["table tbody tr", ".view-details-btn", "[data-testid='row']"],
                    expected_state_change="Detail dialog or expanded view opens",
                ),
            ]

        elif archetype == ApplicationArchetype.FORM_WORKFLOW:
            workflows = [
                PrioritizedWorkflow(
                    name="Complete Required Input Fields",
                    description="Fill out all mandatory inputs, textareas, and selections with valid test data.",
                    archetype_affinity=archetype,
                    priority=0.90,
                    target_selectors=["input[required]", "textarea", "form select"],
                    expected_state_change="Form fields filled with valid values",
                ),
                PrioritizedWorkflow(
                    name="Test Validation Boundaries",
                    description="Trigger input blur or empty submission to verify inline validation indicators.",
                    archetype_affinity=archetype,
                    priority=0.75,
                    target_selectors=["form", "button[type='submit']", ".error-message"],
                    expected_state_change="Inline validation errors properly displayed or cleared",
                ),
                PrioritizedWorkflow(
                    name="Submit Form & Verify Confirmation",
                    description="Submit the completed form and verify success message or transition to next step.",
                    archetype_affinity=archetype,
                    priority=0.85,
                    target_selectors=["button[type='submit']", ".submit-btn", ".success-alert"],
                    expected_state_change="Confirmation banner or step advancement verified",
                ),
            ]

        elif archetype == ApplicationArchetype.E_COMMERCE:
            workflows = [
                PrioritizedWorkflow(
                    name="Browse Catalog & Select Product",
                    description="Search for items, apply price filters, and select product card.",
                    archetype_affinity=archetype,
                    priority=0.90,
                    target_selectors=[".product-card", "input[name='q']", ".filter-category"],
                    expected_state_change="Product detail view loaded",
                ),
                PrioritizedWorkflow(
                    name="Add to Cart & Adjust Quantities",
                    description="Add selected item to cart and verify cart badge counter updates.",
                    archetype_affinity=archetype,
                    priority=0.85,
                    target_selectors=["button.add-to-cart", ".cart-badge", "#cart-btn"],
                    expected_state_change="Cart item count incremented",
                ),
                PrioritizedWorkflow(
                    name="Navigate to Checkout & Verify Order Summary",
                    description="Open cart, proceed to checkout view, and verify item total calculation.",
                    archetype_affinity=archetype,
                    priority=0.75,
                    target_selectors=["#checkout-btn", ".order-summary", ".total-price"],
                    expected_state_change="Checkout summary displayed with correct item subtotal",
                ),
            ]

        else:  # GENERIC_WEB
            workflows = [
                PrioritizedWorkflow(
                    name="Explore Primary Navigation & Viewports",
                    description="Navigate through primary navbar links, headers, and view layouts.",
                    archetype_affinity=archetype,
                    priority=0.85,
                    target_selectors=["nav a", "header a", "main"],
                    expected_state_change="View updates without 404 or broken layout",
                ),
                PrioritizedWorkflow(
                    name="Test Interactive Components & Buttons",
                    description="Interact with primary action buttons, tabs, accordions, and dialog toggles.",
                    archetype_affinity=archetype,
                    priority=0.80,
                    target_selectors=["button", "[role='tab']", "[role='button']"],
                    expected_state_change="Component responds with visible state change",
                ),
                PrioritizedWorkflow(
                    name="Monitor Page Stability & Error Free State",
                    description="Verify that no unhandled page errors or failing HTTP responses occur during interaction.",
                    archetype_affinity=archetype,
                    priority=0.70,
                    target_selectors=["body"],
                    expected_state_change="Clean console and zero unhandled exceptions",
                ),
            ]

        # Prioritize workflows that address known risk areas
        for wf in workflows:
            for risk in risk_areas:
                if any(r in wf.name.lower() or r in wf.description.lower() for r in risk.lower().split("_")):
                    wf.priority = min(wf.priority + 0.1, 1.0)

        return sorted(workflows, key=lambda w: w.priority, reverse=True)

    @classmethod
    def _build_exploration_policy(
        cls,
        archetype: ApplicationArchetype,
        risk_areas: List[str],
    ) -> ExplorationPolicy:
        """Configures exploration parameters."""
        if archetype == ApplicationArchetype.AI_APPLICATION:
            return ExplorationPolicy(
                depth_first_bias=0.6,
                input_variety_weight=0.85,
                error_tolerance=2,
                assertion_density="INTENSIVE",
                defensive_wait_ms=1000,
            )
        elif archetype == ApplicationArchetype.DATA_DASHBOARD:
            return ExplorationPolicy(
                depth_first_bias=0.4,
                input_variety_weight=0.5,
                error_tolerance=3,
                assertion_density="BALANCED",
                defensive_wait_ms=500,
            )
        else:
            return ExplorationPolicy(
                depth_first_bias=0.5,
                input_variety_weight=0.7,
                error_tolerance=2,
                assertion_density="BALANCED",
                defensive_wait_ms=500,
            )

    @classmethod
    def adapt_strategy(
        cls,
        strategy: TestingStrategy,
        step_number: int,
        max_steps: int,
        observation: DOMObservation,
        last_action: Optional[TestAction] = None,
        recent_errors: Optional[List[str]] = None,
    ) -> Tuple[TestingStrategy, Optional[StrategyAdaptationEvent]]:
        """
        Dynamically adjusts the strategy in response to runtime events.
        
        Evaluates:
        1. Action failures and consecutive error threshold (Branches into recovery or skips blocked).
        2. Budget constraints (Prunes low priority workflows when remaining budget < 25%).
        3. Discovered states (Advances completed workflows to next pending priority).
        """
        recent_errors = recent_errors or []
        active_wf = strategy.get_active_workflow()
        budget_ratio = step_number / max(max_steps, 1)

        # Trigger 1: Action Failure / Blocked Workflow
        if last_action and last_action.status == ActionStatus.FAILED:
            if active_wf:
                active_wf.attempts += 1
                if active_wf.attempts >= strategy.exploration_policy.error_tolerance:
                    prev_id = active_wf.workflow_id
                    active_wf.status = WorkflowPriorityStatus.BLOCKED
                    active_wf.verification_notes = f"Blocked after {active_wf.attempts} failed attempts: {last_action.error_message}"
                    
                    # Advance to alternative pending workflow
                    next_wf = strategy.get_next_pending_workflow()
                    if next_wf:
                        next_wf.status = WorkflowPriorityStatus.IN_PROGRESS
                        strategy.active_workflow_id = next_wf.workflow_id
                    else:
                        strategy.active_workflow_id = None

                    event = StrategyAdaptationEvent(
                        step_number=step_number,
                        trigger=StrategyAdaptationTrigger.WORKFLOW_BLOCKED,
                        adaptation_type="SKIP_BLOCKED",
                        reason=f"Workflow '{active_wf.name}' blocked after repeated action failures. Branching to next priority.",
                        previous_active_workflow=prev_id,
                        new_active_workflow=strategy.active_workflow_id,
                        changes={"blocked_workflow": prev_id, "error": last_action.error_message},
                    )
                    strategy.adaptation_history.append(event)
                    strategy.updated_at = datetime.now(timezone.utc).isoformat()
                    logger.info(f"[STRATEGY ADAPT] {event.reason}")
                    return strategy, event

        # Trigger 2: Budget Pressure (Remaining budget < 25%)
        if budget_ratio >= 0.75:
            pending_workflows = [wf for wf in strategy.prioritized_workflows if wf.status == WorkflowPriorityStatus.PENDING]
            if len(pending_workflows) > 1:
                # Prune lowest priority pending workflows to focus on critical path / verification
                pruned_names = []
                for wf in pending_workflows:
                    if wf.priority < 0.85:
                        wf.status = WorkflowPriorityStatus.ABANDONED
                        wf.verification_notes = "Pruned due to remaining step budget constraints."
                        pruned_names.append(wf.name)

                if pruned_names:
                    event = StrategyAdaptationEvent(
                        step_number=step_number,
                        trigger=StrategyAdaptationTrigger.BUDGET_PRESSURE,
                        adaptation_type="PRUNE_BUDGET",
                        reason=f"Step budget pressure ({step_number}/{max_steps}). Pruned non-critical workflows: {', '.join(pruned_names)}",
                        previous_active_workflow=strategy.active_workflow_id,
                        new_active_workflow=strategy.active_workflow_id,
                        changes={"pruned_workflows": pruned_names},
                    )
                    strategy.adaptation_history.append(event)
                    strategy.updated_at = datetime.now(timezone.utc).isoformat()
                    logger.info(f"[STRATEGY ADAPT] {event.reason}")
                    return strategy, event

        # Trigger 3: Observed Workflow Verification (Advance to next workflow)
        if active_wf and active_wf.status == WorkflowPriorityStatus.IN_PROGRESS and last_action and last_action.status == ActionStatus.PASSED:
            # Check if action corresponds to completion of active workflow
            is_verified = False
            desc_lower = (last_action.description or "").lower()
            thought_lower = (last_action.thought or "").lower()

            if "generate" in active_wf.name.lower() and ("generated" in desc_lower or "loading finished" in desc_lower):
                is_verified = True
            elif "parameter" in active_wf.name.lower() and ("input" in desc_lower or "typed" in desc_lower):
                is_verified = True
            elif "contract" in active_wf.name.lower() and ("assert" in desc_lower or "verified" in desc_lower):
                is_verified = True

            if is_verified:
                prev_id = active_wf.workflow_id
                active_wf.status = WorkflowPriorityStatus.VERIFIED
                active_wf.verification_notes = f"Verified by action at step {step_number}: {last_action.description}"

                next_wf = strategy.get_next_pending_workflow()
                if next_wf:
                    next_wf.status = WorkflowPriorityStatus.IN_PROGRESS
                    strategy.active_workflow_id = next_wf.workflow_id
                else:
                    strategy.active_workflow_id = None

                event = StrategyAdaptationEvent(
                    step_number=step_number,
                    trigger=StrategyAdaptationTrigger.EARLY_COMPLETION,
                    adaptation_type="ADVANCE_VERIFIED",
                    reason=f"Workflow '{active_wf.name}' verified. Advancing to next prioritized workflow.",
                    previous_active_workflow=prev_id,
                    new_active_workflow=strategy.active_workflow_id,
                    changes={"verified_workflow": prev_id},
                )
                strategy.adaptation_history.append(event)
                strategy.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"[STRATEGY ADAPT] {event.reason}")
                return strategy, event

        return strategy, None

    @classmethod
    def format_strategy_guidance(
        cls,
        strategy: TestingStrategy,
        current_step: int,
        max_steps: int,
    ) -> str:
        """
        Renders structured, CoT-free strategy instructions for agent reasoning.
        """
        active = strategy.get_active_workflow()
        active_title = active.name if active else "Free Exploration & Verification"
        active_desc = active.description if active else "Explore visible interactive elements and verify system stability."
        selectors = ", ".join(active.target_selectors) if (active and active.target_selectors) else "Interactive elements"

        lines = [
            "=== APPLICATION-ADAPTIVE TESTING STRATEGY ===",
            f"Archetype: {strategy.application_archetype.value} | Mode: {strategy.strategy_mode.value}",
            f"Active Workflow: [{active.status.value if active else 'FREE'}] {active_title}",
            f"Objective: {active_desc}",
            f"Suggested Focus Elements: {selectors}",
        ]

        if strategy.behavioral_contract_ids:
            lines.append(f"Behavioral Contracts: {strategy.behavioral_contract_ids}")

        if strategy.risk_areas:
            lines.append(f"Known Risk Areas: {strategy.risk_areas}")

        lines.append(f"Step Budget: {current_step}/{max_steps} | Policy: {strategy.exploration_policy.assertion_density} assertions")
        lines.append("==============================================")
        return "\n".join(lines)
