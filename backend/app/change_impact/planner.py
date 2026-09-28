"""
Slice 8K — Adaptive Regression Planner

Generates structured regression testing plans with explicit DEEP, TARGETED,
and SMOKE scopes. Every selected item includes machine-readable deterministic
reasons. Enforces exact Git SHA associations (marking plans STALE upon revision drift)
and provides runtime scope expansion when live evidence requires broader testing.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List, Set
from datetime import datetime, timezone
import uuid

from backend.app.change_impact.models import (
    RegressionScope,
    PlanStatus,
    ChangeSet,
    ChangeImpact,
    AffectedWorkflow,
    RegressionPlanItem,
    RegressionScopeExpansion,
    AdaptiveRegressionPlan,
    ImpactLevel,
    ChangeType,
)


class AdaptiveRegressionPlanner:
    """
    Constructs and mutates deterministic regression testing plans.
    """

    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def create_plan(
        self,
        change_set: ChangeSet,
        impact: ChangeImpact,
        target_id: str,
        application_id: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
    ) -> AdaptiveRegressionPlan:
        """
        Deterministically builds an AdaptiveRegressionPlan with DEEP, TARGETED, and SMOKE scopes.
        Each item includes structured deterministic reasons.
        """
        plan_id = f"plan_{uuid.uuid4().hex[:10]}"
        items: List[RegressionPlanItem] = []
        app_id = application_id or change_set.repository or "default_app"

        # Check documentation-only changes
        if change_set.change_types == [ChangeType.DOCUMENTATION]:
            # Documentation change receives only SMOKE coverage
            smoke_item = RegressionPlanItem(
                workflow_id="wf_app_navigation_smoke",
                name="Application Initialization & Navigation Smoke",
                scope=RegressionScope.SMOKE,
                reasons=[
                    "documentation_only_change",
                    "smoke_sanity_preservation_policy"
                ],
                priority=0.3
            )
            items.append(smoke_item)
            return AdaptiveRegressionPlan(
                plan_id=plan_id,
                change_set_id=change_set.change_set_id,
                target_id=target_id,
                application_id=app_id,
                base_commit=change_set.base_commit,
                candidate_commit=change_set.candidate_commit,
                scope_summary={"DEEP": 0, "TARGETED": 0, "SMOKE": 1},
                plan_status=PlanStatus.PLANNED,
                reasoning_summary="Documentation change: bypassing deep and targeted test execution; running basic smoke sanity.",
                impact_summary=impact.summary,
                items=items,
                budget=budget or {"max_steps": 10, "timeout_seconds": 60},
                stale=False
            )

        # Process Workflows into Scopes
        for wf in impact.affected_workflows:
            reasons: List[str] = []
            scope: RegressionScope
            priority: float

            # Determine Scope based on impact level & change types
            if wf.impact_level == ImpactLevel.HIGH:
                scope = RegressionScope.DEEP
                priority = 0.95
                reasons.append(f"direct_dependency_or_primary_target: {wf.reason}")
            elif wf.impact_level == ImpactLevel.MEDIUM:
                scope = RegressionScope.TARGETED
                priority = 0.75
                reasons.append(f"downstream_consumer_or_contract_verification: {wf.reason}")
            else:
                scope = RegressionScope.SMOKE
                priority = 0.40
                reasons.append(f"critical_application_path_smoke_check: {wf.reason}")

            # Correlate with behavioral contracts
            if wf.associated_contracts:
                reasons.append(f"contracts_bound: {', '.join(wf.associated_contracts)}")

            # Correlate with historical memory failure patterns
            relevant_memories = []
            if wf.historical_failures:
                for hf in wf.historical_failures:
                    reasons.append(f"historical_failure_hypothesis: {hf}")
                    relevant_memories.append(hf)
                # Historical failure escalates priority
                priority = min(1.0, priority + 0.05)

            # Correlate with reliability history
            if wf.reliability_history:
                reasons.append(f"reliability_pattern_noted: {wf.reliability_history.get('pattern', 'instability')}")

            items.append(RegressionPlanItem(
                workflow_id=wf.workflow_id,
                name=wf.name,
                scope=scope,
                reasons=reasons,
                relevant_contracts=wf.associated_contracts,
                relevant_memory_ids=relevant_memories,
                priority=priority
            ))

        # Always ensure at least one SMOKE item is present for application sanity
        if not any(item.scope == RegressionScope.SMOKE for item in items):
            items.append(RegressionPlanItem(
                workflow_id="wf_app_navigation_smoke",
                name="Application Initialization & Navigation Smoke",
                scope=RegressionScope.SMOKE,
                reasons=["mandatory_smoke_coverage_policy", "verifies_route_integrity"],
                priority=0.3
            ))

        # Sort items by priority descending
        items.sort(key=lambda x: x.priority, reverse=True)

        scope_summary = {
            "DEEP": sum(1 for it in items if it.scope == RegressionScope.DEEP),
            "TARGETED": sum(1 for it in items if it.scope == RegressionScope.TARGETED),
            "SMOKE": sum(1 for it in items if it.scope == RegressionScope.SMOKE),
        }

        reasoning = (
            f"Adaptive regression plan formulated for candidate {change_set.candidate_commit or 'HEAD'}. "
            f"Allocated {scope_summary['DEEP']} DEEP, {scope_summary['TARGETED']} TARGETED, and "
            f"{scope_summary['SMOKE']} SMOKE test workflows based on explicit impact dependencies and 8E memory."
        )

        return AdaptiveRegressionPlan(
            plan_id=plan_id,
            change_set_id=change_set.change_set_id,
            target_id=target_id,
            application_id=app_id,
            base_commit=change_set.base_commit,
            candidate_commit=change_set.candidate_commit,
            scope_summary=scope_summary,
            plan_status=PlanStatus.PLANNED,
            reasoning_summary=reasoning,
            impact_summary=impact.summary,
            items=items,
            budget=budget or {"max_steps": 30, "timeout_seconds": 180},
            stale=False
        )

    def validate_plan_freshness(self, plan: AdaptiveRegressionPlan, current_candidate_sha: str) -> bool:
        """
        Validates that the plan's candidate_commit exactly matches the candidate commit under test.
        If there is any drift, marks the plan as STALE.
        """
        if not current_candidate_sha or not plan.candidate_commit:
            return True
        if plan.candidate_commit.strip() != current_candidate_sha.strip():
            plan.stale = True
            plan.plan_status = PlanStatus.STALE
            return False
        return True

    def expand_scope(
        self,
        plan: AdaptiveRegressionPlan,
        trigger: str,
        evidence_ids: List[str],
        new_items: List[RegressionPlanItem],
        reason: str,
    ) -> RegressionScopeExpansion:
        """
        Expands the planned regression scope dynamically during execution based on runtime evidence.
        Updates plan items, scope summary, and appends a RegressionScopeExpansion record.
        """
        prev_summary = dict(plan.scope_summary)
        
        # Add new items or upgrade existing items
        existing_ids = {it.workflow_id: it for it in plan.items}
        for item in new_items:
            if item.workflow_id in existing_ids:
                # Upgrade scope if higher
                curr = existing_ids[item.workflow_id]
                if item.scope == RegressionScope.DEEP and curr.scope != RegressionScope.DEEP:
                    curr.scope = RegressionScope.DEEP
                    curr.reasons.append(f"scope_upgraded_by_runtime_evidence: {reason}")
            else:
                item.reasons.append(f"added_by_runtime_evidence: {reason}")
                plan.items.append(item)

        # Recompute scope summary
        plan.scope_summary = {
            "DEEP": sum(1 for it in plan.items if it.scope == RegressionScope.DEEP),
            "TARGETED": sum(1 for it in plan.items if it.scope == RegressionScope.TARGETED),
            "SMOKE": sum(1 for it in plan.items if it.scope == RegressionScope.SMOKE),
        }
        plan.plan_status = PlanStatus.EXPANDED

        expansion = RegressionScopeExpansion(
            plan_id=plan.plan_id,
            trigger=trigger,
            evidence_ids=evidence_ids,
            previous_scope=prev_summary,
            new_scope=plan.scope_summary,
            added_items=new_items,
            reason=reason
        )
        plan.expansions.append(expansion)
        return expansion
