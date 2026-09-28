"""
Slice 8K — Behavioral Comparator & Regression Finding Service

Performs evidence-grounded behavioral comparisons between baseline and candidate runs.
Enforces multi-variable attribution blocking and generates structured regression
findings requiring human governance authorization.
"""

from __future__ import annotations
from typing import Optional, Any, Dict, List, Set
from datetime import datetime, timezone
import uuid

from backend.app.change_impact.models import (
    ComparisonClassification,
    FindingSeverity,
    ChangeSet,
    AdaptiveRegressionPlan,
    BehavioralComparison,
    RegressionFinding,
    ChangeCoverageSummary,
)


class BehavioralComparator:
    """
    Evaluates runtime evidence and contract assertions from independent baseline and candidate runs.
    """

    def compare_runs(
        self,
        plan: AdaptiveRegressionPlan,
        change_set: ChangeSet,
        baseline_run_id: str,
        candidate_run_id: str,
        baseline_results: Dict[str, Any],
        candidate_results: Dict[str, Any],
        contract_evaluations: Optional[Dict[str, bool]] = None,
        evidence_ids: Optional[List[str]] = None,
    ) -> BehavioralComparison:
        """
        Compares baseline and candidate run outcomes.
        Guarantees that baseline and candidate runs are completely separate.
        """
        if baseline_run_id == candidate_run_id:
            raise ValueError(
                f"Independent execution violation: baseline_run_id '{baseline_run_id}' cannot equal "
                f"candidate_run_id '{candidate_run_id}'. Separate execution evidence is mandatory."
            )

        contract_evaluations = contract_evaluations or {}
        evidence_ids = evidence_ids or []
        contract_violations: List[str] = []
        broken_assertions: List[str] = []

        # 1. Evaluate Deterministic Contracts
        for contract_id, passed in contract_evaluations.items():
            if not passed:
                contract_violations.append(contract_id)

        # 2. Check Candidate Assertion Failures vs Baseline
        baseline_passed = baseline_results.get("passed", True)
        candidate_passed = candidate_results.get("passed", True)
        baseline_errors = baseline_results.get("errors", [])
        candidate_errors = candidate_results.get("errors", [])

        if not candidate_passed or candidate_errors:
            for err in candidate_errors:
                if err not in baseline_errors:
                    broken_assertions.append(str(err))

        # 3. Determine Multi-Variable Attribution
        is_multi_var = change_set.is_multi_variable()
        can_attribute = not is_multi_var
        attribution_note = ""
        if is_multi_var:
            attribution_note = (
                "Multiple architectural variables changed simultaneously (e.g. prompt, model, code). "
                "Causal attribution to any single change is blocked without controlled single-variable isolation."
            )

        # 4. Classify Outcome
        classification: ComparisonClassification
        summary: str

        if not baseline_results and not candidate_results:
            classification = ComparisonClassification.INSUFFICIENT_EVIDENCE
            summary = "Insufficient execution evidence in both baseline and candidate runs."
        elif contract_violations or broken_assertions:
            classification = ComparisonClassification.REGRESSION
            summary = (
                f"Regression detected: {len(contract_violations)} contract violations and "
                f"{len(broken_assertions)} new assertion errors in candidate run."
            )
        elif not baseline_passed and candidate_passed:
            classification = ComparisonClassification.IMPROVEMENT
            summary = "Candidate execution succeeded where baseline previously failed. Behavioral improvement verified."
        elif baseline_results.get("output_differs", False) and candidate_passed:
            classification = ComparisonClassification.EXPECTED_CHANGE
            summary = "Behavioral differences observed in candidate output, but all deterministic contracts and assertions passed."
        elif candidate_results.get("new_capabilities_found", False):
            classification = ComparisonClassification.NEW_BEHAVIOR
            summary = "New workflows or capability surfaces discovered; contracts remain intact."
        elif candidate_passed and baseline_passed:
            classification = ComparisonClassification.NO_REGRESSION
            summary = "Baseline and candidate executions both passed all assertions and preserved behavioral contracts."
        else:
            classification = ComparisonClassification.UNKNOWN
            summary = "Inconclusive behavioral comparison."

        comparison = BehavioralComparison(
            plan_id=plan.plan_id,
            change_set_id=change_set.change_set_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            classification=classification,
            is_multi_variable_change=is_multi_var,
            can_attribute_cause=can_attribute,
            attribution_note=attribution_note,
            contract_violations=contract_violations,
            broken_assertions=broken_assertions,
            evidence_ids=evidence_ids,
            summary=summary,
            details={
                "baseline_errors": baseline_errors,
                "candidate_errors": candidate_errors,
                "contract_evaluations": contract_evaluations,
            }
        )

        return comparison

    def generate_findings(
        self,
        comparison: BehavioralComparison,
        plan: AdaptiveRegressionPlan,
    ) -> List[RegressionFinding]:
        """
        Translates a regression comparison into explicit findings requiring human governance.
        """
        findings: List[RegressionFinding] = []

        if comparison.classification != ComparisonClassification.REGRESSION:
            return findings

        # Generate finding for contract violations
        if comparison.contract_violations:
            findings.append(RegressionFinding(
                plan_id=plan.plan_id,
                comparison_id=comparison.comparison_id,
                severity=FindingSeverity.CRITICAL,
                title=f"Behavioral Contract Violations ({len(comparison.contract_violations)})",
                description=(
                    f"Candidate run violated deterministic behavioral contracts: "
                    f"{', '.join(comparison.contract_violations)}. {comparison.attribution_note}"
                ),
                affected_workflows=[item.workflow_id for item in plan.items if item.relevant_contracts],
                affected_contracts=comparison.contract_violations,
                evidence_ids=comparison.evidence_ids,
                recommended_action="Block deployment; investigate candidate changes or update contract if change was intentional.",
                requires_human_governance=True
            ))

        # Generate finding for broken assertions
        if comparison.broken_assertions:
            findings.append(RegressionFinding(
                plan_id=plan.plan_id,
                comparison_id=comparison.comparison_id,
                severity=FindingSeverity.HIGH,
                title="New Runtime Assertion Failures Detected",
                description=f"Candidate run introduced errors absent from baseline: {'; '.join(comparison.broken_assertions)}",
                affected_workflows=[item.workflow_id for item in plan.items if item.scope == "DEEP"],
                affected_contracts=[],
                evidence_ids=comparison.evidence_ids,
                recommended_action="Review error stack trace and DOM telemetry before approving release.",
                requires_human_governance=True
            ))

        return findings
