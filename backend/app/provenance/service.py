"""
Slice 8L — Unified Engineering Provenance Service

Coordinates append-only recording and trace aggregation across the software lifecycle:
Request -> Implementation -> Git Commit -> Pull Request -> AI Review -> CI ->
Application Context -> Change Impact -> Regression Plan -> Lab Execution ->
Evidence -> AI Evaluation -> Diagnosis -> Remediation -> Governance ->
Authorization -> Independent Retest -> Post-Change Verification.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.provenance.models import (
    EngineeringLifecycleEvent,
    LifecycleEventType,
    ActorType,
    ProvenanceTrace,
    ProvenanceChainVerificationResult,
)
from backend.app.provenance.repository import ProvenanceRepository


class ProvenanceService:
    """
    Central service for recording and retrieving end-to-end engineering provenance traces.
    """

    def __init__(self, repository: Optional[ProvenanceRepository] = None):
        self.repo = repository or ProvenanceRepository()

    def record_event(
        self,
        event_type: LifecycleEventType,
        correlation_id: str,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: str = "system",
        application_id: Optional[str] = None,
        target_id: Optional[str] = None,
        run_id: Optional[str] = None,
        test_case_id: Optional[str] = None,
        change_set_id: Optional[str] = None,
        plan_id: Optional[str] = None,
        memory_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        diagnosis_id: Optional[str] = None,
        remediation_id: Optional[str] = None,
        governance_id: Optional[str] = None,
        authorization_id: Optional[str] = None,
        git_commit: Optional[str] = None,
        pull_request_id: Optional[str] = None,
        ci_run_id: Optional[str] = None,
        context_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EngineeringLifecycleEvent:
        """Appends a canonical lifecycle event to the immutable chain."""
        event = EngineeringLifecycleEvent(
            event_type=event_type,
            correlation_id=correlation_id,
            actor_type=actor_type,
            actor_id=actor_id,
            application_id=application_id,
            target_id=target_id,
            run_id=run_id,
            test_case_id=test_case_id,
            change_set_id=change_set_id,
            plan_id=plan_id,
            memory_id=memory_id,
            evidence_id=evidence_id,
            diagnosis_id=diagnosis_id,
            remediation_id=remediation_id,
            governance_id=governance_id,
            authorization_id=authorization_id,
            git_commit=git_commit,
            pull_request_id=pull_request_id,
            ci_run_id=ci_run_id,
            context_id=context_id,
            parent_event_id=parent_event_id,
            metadata=metadata or {},
        )
        return self.repo.append_event(event)

    # -------------------------------------------------------------------------
    # Lifecycle Phase Recorders
    # -------------------------------------------------------------------------

    def record_request(self, correlation_id: str, title: str, description: str, actor_id: str = "human_user") -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.REQUEST_CREATED,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            metadata={"title": title, "description": description}
        )

    def record_commit(self, correlation_id: str, git_commit: str, message: str, actor_id: str = "dev") -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.GIT_COMMIT_CREATED,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            git_commit=git_commit,
            metadata={"message": message}
        )

    def record_pull_request(self, correlation_id: str, pr_id: str, title: str, git_commit: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.PULL_REQUEST_CREATED,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id="dev",
            pull_request_id=pr_id,
            git_commit=git_commit,
            metadata={"title": title}
        )

    def record_ai_review(self, correlation_id: str, pr_id: str, decision: str, findings_count: int) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.AI_REVIEW_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.AI_AGENT,
            actor_id="qwen2.5-coder",
            pull_request_id=pr_id,
            metadata={"decision": decision, "findings_count": findings_count}
        )

    def record_ci(self, correlation_id: str, ci_run_id: str, status: str, git_commit: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.CI_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.CI,
            actor_id="github_actions",
            ci_run_id=ci_run_id,
            git_commit=git_commit,
            metadata={"status": status}
        )

    def record_application_context(self, correlation_id: str, context_id: str, application_id: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.APPLICATION_CONTEXT_BOUND,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="application_context_service",
            context_id=context_id,
            application_id=application_id,
        )

    def record_change_impact(self, correlation_id: str, change_set_id: str, affected_count: int) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.CHANGE_ANALYSIS_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="change_analysis_engine",
            change_set_id=change_set_id,
            metadata={"affected_count": affected_count}
        )

    def record_regression_plan(self, correlation_id: str, plan_id: str, scope_summary: Dict[str, int]) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.REGRESSION_PLAN_CREATED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="adaptive_regression_planner",
            plan_id=plan_id,
            metadata={"scope_summary": scope_summary}
        )

    def record_lab_execution(self, correlation_id: str, run_id: str, target_id: str, status: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.LAB_RUN_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="playwright_runner",
            run_id=run_id,
            target_id=target_id,
            metadata={"status": status}
        )

    def record_evidence(self, correlation_id: str, run_id: str, evidence_id: str, evidence_type: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.EVIDENCE_CAPTURED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="evidence_collector",
            run_id=run_id,
            evidence_id=evidence_id,
            metadata={"evidence_type": evidence_type}
        )

    def record_ai_evaluation(self, correlation_id: str, run_id: str, outcome: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.AI_EVALUATION_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="deterministic_evaluator",
            run_id=run_id,
            metadata={"outcome": outcome}
        )

    def record_diagnosis(self, correlation_id: str, diagnosis_id: str, root_cause: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.DIAGNOSIS_CREATED,
            correlation_id=correlation_id,
            actor_type=ActorType.AI_AGENT,
            actor_id="diagnosis_service",
            diagnosis_id=diagnosis_id,
            metadata={"root_cause": root_cause}
        )

    def record_remediation(self, correlation_id: str, remediation_id: str, status: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.REMEDIATION_PROPOSED,
            correlation_id=correlation_id,
            actor_type=ActorType.AI_AGENT,
            actor_id="remediation_service",
            remediation_id=remediation_id,
            metadata={"status": status}
        )

    def record_governance_decision(self, correlation_id: str, governance_id: str, decision: str, actor_id: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.HUMAN_DECISION_RECORDED,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id=actor_id,
            governance_id=governance_id,
            metadata={"decision": decision}
        )

    def record_authorization(self, correlation_id: str, authorization_id: str, scope: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.CHANGE_AUTHORIZED,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id="governance_board",
            authorization_id=authorization_id,
            metadata={"scope": scope}
        )

    def record_independent_retest(self, correlation_id: str, run_id: str, status: str) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.INDEPENDENT_RETEST_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="ai_agent_runner",
            run_id=run_id,
            metadata={"status": status}
        )

    def record_post_change_verification(self, correlation_id: str, application_id: str, verified: bool) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.POST_CHANGE_VERIFICATION_COMPLETED,
            correlation_id=correlation_id,
            actor_type=ActorType.SYSTEM,
            actor_id="reliability_service",
            application_id=application_id,
            metadata={"verified": verified}
        )

    def record_correction(self, correlation_id: str, target_event_id: str, rationale: str, details: Dict[str, Any]) -> EngineeringLifecycleEvent:
        return self.record_event(
            event_type=LifecycleEventType.EVENT_CORRECTION,
            correlation_id=correlation_id,
            actor_type=ActorType.HUMAN,
            actor_id="compliance_officer",
            parent_event_id=target_event_id,
            metadata={"target_event_id": target_event_id, "rationale": rationale, "details": details}
        )

    # -------------------------------------------------------------------------
    # Queries & Trace Aggregation
    # -------------------------------------------------------------------------

    def get_event(self, event_id: str) -> Optional[EngineeringLifecycleEvent]:
        return self.repo.get_event(event_id)

    def get_provenance_trace(self, correlation_id: str) -> ProvenanceTrace:
        """Retrieves and stitches together the full chronological journey for a correlation thread."""
        events = self.repo.list_events(correlation_id=correlation_id, limit=5000)
        stages = sorted(list(set(e.event_type.value for e in events)))

        # Define key milestones for completeness
        core_stages = {
            "REQUEST_CREATED",
            "GIT_COMMIT_CREATED",
            "PULL_REQUEST_CREATED",
            "CI_COMPLETED",
            "REGRESSION_PLAN_CREATED",
            "LAB_RUN_COMPLETED",
            "HUMAN_DECISION_RECORDED",
            "CHANGE_AUTHORIZED"
        }
        has_core = core_stages.issubset(set(stages))

        summary = (
            f"Provenance trace for '{correlation_id}' contains {len(events)} events across {len(stages)} distinct stages. "
            f"Chain verification status: {'COMPLETE' if has_core else 'IN_PROGRESS'}."
        )

        return ProvenanceTrace(
            correlation_id=correlation_id,
            events=events,
            stages_present=stages,
            is_complete_lifecycle=has_core,
            total_events=len(events),
            summary=summary
        )

    def verify_chain(self, correlation_id: Optional[str] = None) -> ProvenanceChainVerificationResult:
        """Audits the cryptographic event chain."""
        return self.repo.verify_chain(correlation_id=correlation_id)
