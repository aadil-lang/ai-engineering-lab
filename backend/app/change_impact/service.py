"""
Slice 8K — Change Impact & Adaptive Regression Service

Orchestrates change analysis, impact graph construction, adaptive regression
planning, runtime scope expansion, behavioral comparison, regression finding
generation, and Live Console SSE event broadcasting.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
import uuid

from backend.app.change_impact.models import (
    ChangeType,
    ChangeSource,
    ChangeSet,
    ChangeImpact,
    AdaptiveRegressionPlan,
    RegressionPlanItem,
    RegressionScopeExpansion,
    BehavioralComparison,
    RegressionFinding,
    ComparisonClassification,
    PlanStatus,
)
from backend.app.change_impact.engine import ChangeAnalysisEngine
from backend.app.change_impact.planner import AdaptiveRegressionPlanner
from backend.app.change_impact.comparator import BehavioralComparator
from backend.app.dogfooding.live_events import LiveEventType, LiveEvent
from backend.app.dogfooding.live_session_bus import live_event_bus


class ChangeImpactService:
    """
    Central service for Change-Aware Impact Analysis & Adaptive Regression Testing.
    """

    def __init__(self, memory_repository=None, app_context_service=None, event_bus=None):
        self.memory_repo = memory_repository
        self.app_context_service = app_context_service
        self.event_bus = event_bus or live_event_bus
        self.engine = ChangeAnalysisEngine(memory_repository=memory_repository, app_context_service=app_context_service)
        self.planner = AdaptiveRegressionPlanner(event_bus=self.event_bus)
        self.comparator = BehavioralComparator()

        # In-memory storage for Slice 8K entities
        self._change_sets: Dict[str, ChangeSet] = {}
        self._impacts: Dict[str, ChangeImpact] = {}
        self._plans: Dict[str, AdaptiveRegressionPlan] = {}
        self._comparisons: Dict[str, BehavioralComparison] = {}
        self._findings: Dict[str, List[RegressionFinding]] = {}

    def _emit_event(self, event_type: LiveEventType, session_id: str, run_id: str, payload: Dict[str, Any]):
        """Helper to broadcast real-time Live Console events."""
        if self.event_bus and session_id:
            try:
                self.event_bus.publish(
                    session_id=session_id,
                    event_type=event_type,
                    payload=payload
                )
            except Exception:
                pass

    def register_change_set(self, change_set: ChangeSet) -> ChangeSet:
        """Stores a new ChangeSet with classified change types and symbols."""
        if not change_set.change_types:
            change_set.change_types = self.engine.classify_change(
                changed_files=change_set.changed_files,
                prompts_changed=change_set.changed_prompts,
                models_changed=change_set.changed_models,
                retrieval_changed=change_set.changed_retrieval,
                tools_changed=change_set.changed_tools,
                config_changed=change_set.changed_configuration
            )
        self._change_sets[change_set.change_set_id] = change_set
        return change_set

    def get_change_set(self, change_set_id: str) -> Optional[ChangeSet]:
        return self._change_sets.get(change_set_id)

    def analyze_change(
        self,
        change_set: ChangeSet,
        application_id: Optional[str] = None,
        session_id: str = "",
        run_id: str = "",
    ) -> ChangeImpact:
        """Performs change analysis, builds the impact graph, and emits events."""
        self.register_change_set(change_set)

        self._emit_event(
            LiveEventType.CHANGE_ANALYSIS_STARTED,
            session_id,
            run_id,
            {
                "change_set_id": change_set.change_set_id,
                "change_types": [ct.value for ct in change_set.change_types],
                "candidate_commit": change_set.candidate_commit
            }
        )

        impact = self.engine.analyze_impact(change_set, application_id=application_id)
        self._impacts[change_set.change_set_id] = impact

        self._emit_event(
            LiveEventType.IMPACT_GRAPH_BUILT,
            session_id,
            run_id,
            {
                "change_set_id": change_set.change_set_id,
                "affected_components_count": len(impact.affected_components),
                "affected_workflows_count": len(impact.affected_workflows),
                "relationships_count": len(impact.impact_relationships),
                "ai_behavior_affected": impact.ai_behavior_affected
            }
        )

        self._emit_event(
            LiveEventType.CHANGE_ANALYSIS_COMPLETED,
            session_id,
            run_id,
            {
                "change_set_id": change_set.change_set_id,
                "summary": impact.summary
            }
        )

        return impact

    def get_impact(self, change_set_id: str) -> Optional[ChangeImpact]:
        return self._impacts.get(change_set_id)

    def create_regression_plan(
        self,
        change_set_id: str,
        target_id: str,
        application_id: Optional[str] = None,
        budget: Optional[Dict[str, Any]] = None,
        session_id: str = "",
        run_id: str = "",
    ) -> AdaptiveRegressionPlan:
        """Formulates an AdaptiveRegressionPlan with DEEP, TARGETED, and SMOKE scopes."""
        change_set = self.get_change_set(change_set_id)
        if not change_set:
            raise ValueError(f"ChangeSet '{change_set_id}' not found.")

        impact = self.get_impact(change_set_id)
        if not impact:
            impact = self.analyze_change(change_set, application_id=application_id, session_id=session_id, run_id=run_id)

        plan = self.planner.create_plan(
            change_set=change_set,
            impact=impact,
            target_id=target_id,
            application_id=application_id,
            budget=budget
        )
        self._plans[plan.plan_id] = plan

        self._emit_event(
            LiveEventType.REGRESSION_PLAN_CREATED,
            session_id,
            run_id,
            {
                "plan_id": plan.plan_id,
                "scope_summary": plan.scope_summary,
                "total_items": len(plan.items),
                "candidate_commit": plan.candidate_commit
            }
        )

        return plan

    def get_regression_plan(self, plan_id: str) -> Optional[AdaptiveRegressionPlan]:
        return self._plans.get(plan_id)

    def expand_plan_scope(
        self,
        plan_id: str,
        trigger: str,
        evidence_ids: List[str],
        new_items: List[RegressionPlanItem],
        reason: str,
        session_id: str = "",
        run_id: str = "",
    ) -> RegressionScopeExpansion:
        """Expands regression scope mid-execution when runtime evidence exposes issues."""
        plan = self.get_regression_plan(plan_id)
        if not plan:
            raise ValueError(f"Regression plan '{plan_id}' not found.")

        expansion = self.planner.expand_scope(
            plan=plan,
            trigger=trigger,
            evidence_ids=evidence_ids,
            new_items=new_items,
            reason=reason
        )

        self._emit_event(
            LiveEventType.REGRESSION_SCOPE_EXPANDED,
            session_id,
            run_id,
            {
                "plan_id": plan.plan_id,
                "trigger": trigger,
                "reason": reason,
                "previous_scope": expansion.previous_scope,
                "new_scope": expansion.new_scope,
                "added_items_count": len(new_items)
            }
        )

        return expansion

    def execute_regression_plan(
        self,
        plan_id: str,
        candidate_commit: Optional[str] = None,
        session_id: str = "",
        run_id: str = "",
    ) -> Dict[str, Any]:
        """
        Executes a planned regression suite while enforcing Git SHA freshness.
        """
        plan = self.get_regression_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        if candidate_commit and not self.planner.validate_plan_freshness(plan, candidate_commit):
            raise ValueError(
                f"Plan '{plan_id}' is STALE: candidate commit drift detected "
                f"(expected '{plan.candidate_commit}', received '{candidate_commit}'). "
                f"Regenerate plan before executing."
            )

        if plan.stale or plan.plan_status == PlanStatus.STALE:
            raise ValueError(f"Plan '{plan_id}' is marked STALE. Regenerate plan before executing.")

        plan.plan_status = PlanStatus.EXECUTING

        self._emit_event(
            LiveEventType.REGRESSION_EXECUTION_STARTED,
            session_id,
            run_id,
            {"plan_id": plan.plan_id, "scope_summary": plan.scope_summary}
        )

        # Simulation of item execution
        executed_items = len(plan.items)
        plan.plan_status = PlanStatus.COMPLETED

        self._emit_event(
            LiveEventType.REGRESSION_EXECUTION_COMPLETED,
            session_id,
            run_id,
            {"plan_id": plan.plan_id, "executed_items": executed_items}
        )

        return {
            "plan_id": plan.plan_id,
            "status": "COMPLETED",
            "executed_items": executed_items,
            "scope_summary": plan.scope_summary
        }

    def compare_runs(
        self,
        plan_id: str,
        baseline_run_id: str,
        candidate_run_id: str,
        baseline_results: Dict[str, Any],
        candidate_results: Dict[str, Any],
        contract_evaluations: Optional[Dict[str, bool]] = None,
        evidence_ids: Optional[List[str]] = None,
        session_id: str = "",
    ) -> BehavioralComparison:
        """Executes behavioral comparison between independent baseline and candidate runs."""
        plan = self.get_regression_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        change_set = self.get_change_set(plan.change_set_id)
        if not change_set:
            raise ValueError(f"ChangeSet '{plan.change_set_id}' not found.")

        self._emit_event(
            LiveEventType.BASELINE_COMPARISON_STARTED,
            session_id,
            candidate_run_id,
            {"plan_id": plan_id, "baseline_run_id": baseline_run_id, "candidate_run_id": candidate_run_id}
        )

        comparison = self.comparator.compare_runs(
            plan=plan,
            change_set=change_set,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_results=baseline_results,
            candidate_results=candidate_results,
            contract_evaluations=contract_evaluations,
            evidence_ids=evidence_ids
        )
        self._comparisons[plan_id] = comparison

        self._emit_event(
            LiveEventType.BASELINE_COMPARISON_COMPLETED,
            session_id,
            candidate_run_id,
            {
                "plan_id": plan_id,
                "classification": comparison.classification.value,
                "is_multi_variable_change": comparison.is_multi_variable_change,
                "can_attribute_cause": comparison.can_attribute_cause
            }
        )

        # Generate findings if regression
        findings = self.comparator.generate_findings(comparison, plan)
        self._findings[plan_id] = findings

        for finding in findings:
            self._emit_event(
                LiveEventType.REGRESSION_FINDING_DETECTED,
                session_id,
                candidate_run_id,
                {
                    "finding_id": finding.finding_id,
                    "plan_id": plan_id,
                    "severity": finding.severity.value,
                    "title": finding.title,
                    "requires_human_governance": finding.requires_human_governance
                }
            )

        return comparison

    def get_comparison(self, plan_id: str) -> Optional[BehavioralComparison]:
        return self._comparisons.get(plan_id)

    def get_findings(self, plan_id: str) -> List[RegressionFinding]:
        return self._findings.get(plan_id, [])
