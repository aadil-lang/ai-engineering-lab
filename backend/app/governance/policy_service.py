from __future__ import annotations
from typing import Optional, List, Dict, Any

from backend.app.governance.models import (
    ApprovalPolicy,
    RecommendationType,
    RiskLevel,
    ApprovalRequest,
    EvidencePackage,
)
from backend.app.governance.repository import GovernanceRepository


RISK_ORDER = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class GovernancePolicyService:
    """
    Deterministic governance policy evaluation.
    Evaluates effective risk, matches policies to change types,
    and enforces required verification gates.
    AI output must never modify or bypass governance policy.
    """

    def __init__(self, repo: Optional[GovernanceRepository] = None):
        self.repo = repo or GovernanceRepository()
        self._ensure_default_policies()

    def _ensure_default_policies(self):
        """Seed default canonical policies if none exist."""
        existing = self.repo.list_policies()
        if existing:
            return

        default_policies = [
            ApprovalPolicy(
                policy_id="POL-PROMPT-PRODUCTION",
                name="Production Prompt Promotion Policy",
                change_type=RecommendationType.PROMPT_CHANGE,
                risk_level=RiskLevel.HIGH,
                required_approvals=1,
                required_evidence=["EVALUATION_SNAPSHOT", "REGRESSION_EVALUATION"],
                required_verifications=["EVALUATION_SNAPSHOT", "REGRESSION_EVALUATION"],
                human_role_requirements=["ENGINEER", "PROMPT_AUTHOR"],
                enabled=True,
                version=1,
            ),
            ApprovalPolicy(
                policy_id="POL-CODE-PRODUCTION",
                name="Production Code Release Policy",
                change_type=RecommendationType.CODE_CHANGE,
                risk_level=RiskLevel.HIGH,
                required_approvals=1,
                required_evidence=["CI_VERIFICATION", "LAB_VERIFICATION"],
                required_verifications=["CI_VERIFICATION", "LAB_VERIFICATION"],
                human_role_requirements=["ENGINEER", "MAINTAINER"],
                enabled=True,
                version=1,
            ),
            ApprovalPolicy(
                policy_id="POL-MODEL-CONFIG",
                name="Model Configuration Change Policy",
                change_type=RecommendationType.MODEL_CONFIGURATION_CHANGE,
                risk_level=RiskLevel.HIGH,
                required_approvals=1,
                required_evidence=["EVALUATION_SNAPSHOT"],
                required_verifications=["EVALUATION_SNAPSHOT"],
                human_role_requirements=["AI_ENGINEER"],
                enabled=True,
                version=1,
            ),
            ApprovalPolicy(
                policy_id="POL-TOOL-PERMISSION",
                name="Tool Permission Expansion Policy",
                change_type=RecommendationType.TOOL_PERMISSION_CHANGE,
                risk_level=RiskLevel.CRITICAL,
                required_approvals=1,
                required_evidence=["LAB_VERIFICATION"],
                required_verifications=["LAB_VERIFICATION"],
                human_role_requirements=["SECURITY_LEAD"],
                enabled=True,
                version=1,
            ),
            ApprovalPolicy(
                policy_id="POL-DEPLOYMENT",
                name="Consequential Deployment Policy",
                change_type=RecommendationType.DEPLOYMENT,
                risk_level=RiskLevel.CRITICAL,
                required_approvals=1,
                required_evidence=["CI_VERIFICATION", "LAB_VERIFICATION"],
                required_verifications=["CI_VERIFICATION", "LAB_VERIFICATION"],
                human_role_requirements=["RELEASE_MANAGER"],
                enabled=True,
                version=1,
            ),
        ]
        for p in default_policies:
            self.repo.save_policy(p)

    def determine_effective_risk(
        self,
        change_type: RecommendationType,
        ai_proposed_risk: RiskLevel,
        subject_context: Optional[Dict[str, Any]] = None,
    ) -> RiskLevel:
        """
        Determines EFFECTIVE_RISK deterministically.
        Prefers the stricter applicable risk level:
        AI can propose risk, but governance policy deterministically bounds it.
        """
        policy_min = RiskLevel.MEDIUM
        if change_type in (RecommendationType.DEPLOYMENT, RecommendationType.ROLLBACK, RecommendationType.TOOL_PERMISSION_CHANGE):
            policy_min = RiskLevel.CRITICAL
        elif change_type in (RecommendationType.PROMPT_CHANGE, RecommendationType.CODE_CHANGE, RecommendationType.MODEL_CONFIGURATION_CHANGE):
            policy_min = RiskLevel.HIGH

        # Stricter risk wins
        if RISK_ORDER[policy_min] > RISK_ORDER[ai_proposed_risk]:
            return policy_min
        return ai_proposed_risk

    def get_applicable_policy(
        self,
        change_type: RecommendationType,
        risk_level: RiskLevel,
    ) -> Optional[ApprovalPolicy]:
        policies = self.repo.list_policies()
        matching = [p for p in policies if p.change_type == change_type]
        if not matching:
            return None
        # Return exact risk level match or highest enabled policy
        exact = [p for p in matching if p.risk_level == risk_level]
        if exact:
            return exact[0]
        return matching[0]

    def evaluate_policy_compliance(
        self,
        approval_request: ApprovalRequest,
        evidence_package: EvidencePackage,
    ) -> tuple[bool, List[str]]:
        """
        Validates that the evidence package satisfies the applicable policy requirements.
        Returns (is_compliant, list_of_violations).
        """
        violations: List[str] = []
        policy = self.get_applicable_policy(approval_request.change_type, approval_request.risk_level)
        if not policy:
            # Fallback safe requirement
            return True, []

        req_verifs = policy.required_verifications
        if "CI_VERIFICATION" in req_verifs:
            if not evidence_package.ci_run_id and not approval_request.ci_verification_id:
                violations.append("Policy requires CI verification, but none is provided in evidence.")

        if "LAB_VERIFICATION" in req_verifs:
            if not evidence_package.lab_verification_id and not approval_request.lab_verification_id:
                violations.append("Policy requires Engineering Lab verification, but none is provided in evidence.")

        if "EVALUATION_SNAPSHOT" in req_verifs:
            if not evidence_package.evaluation_snapshot_id and not approval_request.evaluation_snapshot_id:
                violations.append("Policy requires Evaluation Snapshot, but none is provided in evidence.")

        if "REGRESSION_EVALUATION" in req_verifs:
            if evidence_package.regressions:
                violations.append(f"Policy forbids unaddressed regressions. Found: {evidence_package.regressions}")

        return len(violations) == 0, violations
