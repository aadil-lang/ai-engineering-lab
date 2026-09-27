from __future__ import annotations
import sqlite3
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.governance.models import (
    GovernanceRecommendation,
    ApprovalRequest,
    ApprovalRequestStatus,
    HumanDecision,
    ChangeAuthorization,
    AuthorizationStatus,
    ApprovalPolicy,
    EvidencePackage,
    GovernanceAuditRecord,
    RecommendationType,
    RiskLevel,
    DecisionType,
    ActorType,
)
from backend.app.governance.errors import (
    ApprovalRequestImmutableError,
    InvalidApprovalStateTransitionError,
    EvidencePackageTamperedError,
    ChangeAuthorizationNotFoundError,
)


class GovernanceRepository:
    """
    SQLite-backed repository for Human Governance & Change Authorization.
    Enforces immutability on approval requests, evidence verification,
    and append-only tamper-evident audit logging.
    """

    def __init__(self, db_path: str = "backend/data/governance.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Recommendations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    recommendation_type TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_run_id TEXT,
                    source_evaluation_id TEXT,
                    source_diagnosis_id TEXT,
                    source_evidence_ids TEXT,
                    proposed_action TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    epistemic_status TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    effective_risk TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )

            # 2. Evidence Packages
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_packages (
                    package_id TEXT PRIMARY KEY,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    git_commit_sha TEXT,
                    prompt_version TEXT,
                    model_version TEXT,
                    evaluation_snapshot_id TEXT,
                    ci_run_id TEXT,
                    lab_verification_id TEXT,
                    diagnosis_ids TEXT,
                    recommendation_ids TEXT,
                    observations TEXT,
                    failures TEXT,
                    regressions TEXT,
                    verification_results TEXT,
                    created_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                )
                """
            )

            # 3. Approval Requests
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_requests (
                    approval_request_id TEXT PRIMARY KEY,
                    recommendation_id TEXT,
                    change_type TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    current_version TEXT,
                    proposed_version TEXT,
                    proposed_commit_sha TEXT,
                    evaluation_snapshot_id TEXT,
                    lab_verification_id TEXT,
                    ci_verification_id TEXT,
                    evidence_package_id TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    required_approval_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
                """
            )

            # 4. Human Decisions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS human_decisions (
                    decision_id TEXT PRIMARY KEY,
                    approval_request_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    decision_maker_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    decision_timestamp TEXT NOT NULL,
                    decision_reason TEXT NOT NULL,
                    evidence_acknowledged INTEGER NOT NULL,
                    version_acknowledged INTEGER NOT NULL,
                    commit_acknowledged INTEGER NOT NULL
                )
                """
            )

            # 5. Change Authorizations
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS change_authorizations (
                    authorization_id TEXT PRIMARY KEY,
                    approval_request_id TEXT NOT NULL,
                    decision_id TEXT NOT NULL,
                    authorized_change_type TEXT NOT NULL,
                    authorized_subject TEXT NOT NULL,
                    authorized_version TEXT,
                    authorized_commit_sha TEXT,
                    authorization_scope TEXT NOT NULL,
                    evidence_package_id TEXT NOT NULL,
                    evidence_package_hash TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            # 6. Approval Policies
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_policies (
                    policy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    required_approvals INTEGER NOT NULL,
                    required_evidence TEXT,
                    required_verifications TEXT,
                    human_role_requirements TEXT,
                    enabled INTEGER NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )

            # 7. Audit Trail (append-only)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_audit (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    subject_type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    previous_state TEXT,
                    new_state TEXT,
                    timestamp TEXT NOT NULL,
                    evidence_package_id TEXT,
                    approval_request_id TEXT,
                    authorization_id TEXT,
                    content_hash TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """
            )

            conn.commit()

    # --- Recommendations ---

    def save_recommendation(self, rec: GovernanceRecommendation) -> GovernanceRecommendation:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO governance_recommendations (
                    recommendation_id, recommendation_type, subject_type, subject_id,
                    source_system, source_run_id, source_evaluation_id, source_diagnosis_id,
                    source_evidence_ids, proposed_action, rationale, epistemic_status,
                    risk_level, effective_risk, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.recommendation_id,
                    rec.recommendation_type.value,
                    rec.subject_type,
                    rec.subject_id,
                    rec.source_system,
                    rec.source_run_id,
                    rec.source_evaluation_id,
                    rec.source_diagnosis_id,
                    json.dumps(rec.source_evidence_ids),
                    rec.proposed_action,
                    rec.rationale,
                    rec.epistemic_status,
                    rec.risk_level.value,
                    rec.effective_risk.value if rec.effective_risk else None,
                    rec.created_at,
                    rec.expires_at,
                ),
            )
            conn.commit()
        return rec

    def get_recommendation(self, rec_id: str) -> Optional[GovernanceRecommendation]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM governance_recommendations WHERE recommendation_id = ?", (rec_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_recommendation(row)

    def list_recommendations(self) -> List[GovernanceRecommendation]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM governance_recommendations ORDER BY created_at DESC")
            return [self._row_to_recommendation(r) for r in cursor.fetchall()]

    def _row_to_recommendation(self, row: sqlite3.Row) -> GovernanceRecommendation:
        return GovernanceRecommendation(
            recommendation_id=row["recommendation_id"],
            recommendation_type=RecommendationType(row["recommendation_type"]),
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            source_system=row["source_system"],
            source_run_id=row["source_run_id"],
            source_evaluation_id=row["source_evaluation_id"],
            source_diagnosis_id=row["source_diagnosis_id"],
            source_evidence_ids=json.loads(row["source_evidence_ids"] or "[]"),
            proposed_action=row["proposed_action"],
            rationale=row["rationale"],
            epistemic_status=row["epistemic_status"],
            risk_level=RiskLevel(row["risk_level"]),
            effective_risk=RiskLevel(row["effective_risk"]) if row["effective_risk"] else None,
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    # --- Evidence Packages ---

    def save_evidence_package(self, pkg: EvidencePackage) -> EvidencePackage:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # If already exists, check hash match
            cursor.execute("SELECT content_hash FROM evidence_packages WHERE package_id = ?", (pkg.package_id,))
            row = cursor.fetchone()
            if row and row["content_hash"] != pkg.content_hash:
                raise EvidencePackageTamperedError(
                    f"Evidence package {pkg.package_id} already exists with differing content hash."
                )

            cursor.execute(
                """
                INSERT OR REPLACE INTO evidence_packages (
                    package_id, subject_type, subject_id, git_commit_sha, prompt_version,
                    model_version, evaluation_snapshot_id, ci_run_id, lab_verification_id,
                    diagnosis_ids, recommendation_ids, observations, failures, regressions,
                    verification_results, created_at, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pkg.package_id,
                    pkg.subject_type,
                    pkg.subject_id,
                    pkg.git_commit_sha,
                    pkg.prompt_version,
                    pkg.model_version,
                    pkg.evaluation_snapshot_id,
                    pkg.ci_run_id,
                    pkg.lab_verification_id,
                    json.dumps(pkg.diagnosis_ids),
                    json.dumps(pkg.recommendation_ids),
                    json.dumps(pkg.observations),
                    json.dumps(pkg.failures),
                    json.dumps(pkg.regressions),
                    json.dumps(pkg.verification_results),
                    pkg.created_at,
                    pkg.content_hash,
                ),
            )
            conn.commit()
        return pkg

    def get_evidence_package(self, pkg_id: str) -> Optional[EvidencePackage]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evidence_packages WHERE package_id = ?", (pkg_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_evidence_package(row)

    def _row_to_evidence_package(self, row: sqlite3.Row) -> EvidencePackage:
        return EvidencePackage(
            package_id=row["package_id"],
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            git_commit_sha=row["git_commit_sha"],
            prompt_version=row["prompt_version"],
            model_version=row["model_version"],
            evaluation_snapshot_id=row["evaluation_snapshot_id"],
            ci_run_id=row["ci_run_id"],
            lab_verification_id=row["lab_verification_id"],
            diagnosis_ids=json.loads(row["diagnosis_ids"] or "[]"),
            recommendation_ids=json.loads(row["recommendation_ids"] or "[]"),
            observations=json.loads(row["observations"] or "[]"),
            failures=json.loads(row["failures"] or "[]"),
            regressions=json.loads(row["regressions"] or "[]"),
            verification_results=json.loads(row["verification_results"] or "{}"),
            created_at=row["created_at"],
            content_hash=row["content_hash"],
        )

    # --- Approval Requests ---

    def save_approval_request(self, req: ApprovalRequest) -> ApprovalRequest:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approval_requests WHERE approval_request_id = ?", (req.approval_request_id,))
            existing = cursor.fetchone()

            if existing:
                # Content immutability checks
                if (
                    existing["change_type"] != req.change_type.value
                    or existing["subject_type"] != req.subject_type
                    or existing["subject_id"] != req.subject_id
                    or existing["proposed_version"] != req.proposed_version
                    or existing["proposed_commit_sha"] != req.proposed_commit_sha
                    or existing["evidence_package_id"] != req.evidence_package_id
                ):
                    raise ApprovalRequestImmutableError(
                        f"ApprovalRequest {req.approval_request_id} content is immutable once created."
                    )

                # Valid status transitions
                old_status = ApprovalRequestStatus(existing["status"])
                new_status = req.status
                if old_status != new_status:
                    if old_status != ApprovalRequestStatus.PENDING:
                        raise InvalidApprovalStateTransitionError(
                            f"Cannot transition approval request from {old_status} to {new_status}."
                        )

            cursor.execute(
                """
                INSERT OR REPLACE INTO approval_requests (
                    approval_request_id, recommendation_id, change_type, subject_type,
                    subject_id, current_version, proposed_version, proposed_commit_sha,
                    evaluation_snapshot_id, lab_verification_id, ci_verification_id,
                    evidence_package_id, risk_level, required_approval_count, status,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    req.approval_request_id,
                    req.recommendation_id,
                    req.change_type.value,
                    req.subject_type,
                    req.subject_id,
                    req.current_version,
                    req.proposed_version,
                    req.proposed_commit_sha,
                    req.evaluation_snapshot_id,
                    req.lab_verification_id,
                    req.ci_verification_id,
                    req.evidence_package_id,
                    req.risk_level.value,
                    req.required_approval_count,
                    req.status.value,
                    req.created_at,
                    req.expires_at,
                ),
            )
            conn.commit()
        return req

    def get_approval_request(self, req_id: str) -> Optional[ApprovalRequest]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approval_requests WHERE approval_request_id = ?", (req_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_approval_request(row)

    def list_approval_requests(self, status: Optional[ApprovalRequestStatus] = None) -> List[ApprovalRequest]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM approval_requests WHERE status = ? ORDER BY created_at DESC",
                    (status.value,),
                )
            else:
                cursor.execute("SELECT * FROM approval_requests ORDER BY created_at DESC")
            return [self._row_to_approval_request(r) for r in cursor.fetchall()]

    def _row_to_approval_request(self, row: sqlite3.Row) -> ApprovalRequest:
        return ApprovalRequest(
            approval_request_id=row["approval_request_id"],
            recommendation_id=row["recommendation_id"],
            change_type=RecommendationType(row["change_type"]),
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            current_version=row["current_version"],
            proposed_version=row["proposed_version"],
            proposed_commit_sha=row["proposed_commit_sha"],
            evaluation_snapshot_id=row["evaluation_snapshot_id"],
            lab_verification_id=row["lab_verification_id"],
            ci_verification_id=row["ci_verification_id"],
            evidence_package_id=row["evidence_package_id"],
            risk_level=RiskLevel(row["risk_level"]),
            required_approval_count=row["required_approval_count"],
            status=ApprovalRequestStatus(row["status"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    # --- Human Decisions ---

    def save_decision(self, decision: HumanDecision) -> HumanDecision:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO human_decisions (
                    decision_id, approval_request_id, decision, decision_maker_id,
                    actor_type, decision_timestamp, decision_reason,
                    evidence_acknowledged, version_acknowledged, commit_acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.approval_request_id,
                    decision.decision.value,
                    decision.decision_maker_id,
                    decision.actor_type.value,
                    decision.decision_timestamp,
                    decision.decision_reason,
                    1 if decision.evidence_acknowledged else 0,
                    1 if decision.version_acknowledged else 0,
                    1 if decision.commit_acknowledged else 0,
                ),
            )
            conn.commit()
        return decision

    def get_decision(self, decision_id: str) -> Optional[HumanDecision]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM human_decisions WHERE decision_id = ?", (decision_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)

    def get_decision_for_request(self, request_id: str) -> Optional[HumanDecision]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM human_decisions WHERE approval_request_id = ? ORDER BY decision_timestamp DESC LIMIT 1",
                (request_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)

    def _row_to_decision(self, row: sqlite3.Row) -> HumanDecision:
        return HumanDecision(
            decision_id=row["decision_id"],
            approval_request_id=row["approval_request_id"],
            decision=DecisionType(row["decision"]),
            decision_maker_id=row["decision_maker_id"],
            actor_type=ActorType(row["actor_type"]),
            decision_timestamp=row["decision_timestamp"],
            decision_reason=row["decision_reason"],
            evidence_acknowledged=bool(row["evidence_acknowledged"]),
            version_acknowledged=bool(row["version_acknowledged"]),
            commit_acknowledged=bool(row["commit_acknowledged"]),
        )

    # --- Change Authorizations ---

    def save_authorization(self, auth: ChangeAuthorization) -> ChangeAuthorization:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO change_authorizations (
                    authorization_id, approval_request_id, decision_id,
                    authorized_change_type, authorized_subject, authorized_version,
                    authorized_commit_sha, authorization_scope, evidence_package_id,
                    evidence_package_hash, issued_at, expires_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    auth.authorization_id,
                    auth.approval_request_id,
                    auth.decision_id,
                    auth.authorized_change_type.value,
                    auth.authorized_subject,
                    auth.authorized_version,
                    auth.authorized_commit_sha,
                    auth.authorization_scope,
                    auth.evidence_package_id,
                    auth.evidence_package_hash,
                    auth.issued_at,
                    auth.expires_at,
                    auth.status.value,
                ),
            )
            conn.commit()
        return auth

    def get_authorization(self, auth_id: str) -> Optional[ChangeAuthorization]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM change_authorizations WHERE authorization_id = ?", (auth_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_authorization(row)

    def list_authorizations(self, status: Optional[AuthorizationStatus] = None) -> List[ChangeAuthorization]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM change_authorizations WHERE status = ? ORDER BY issued_at DESC",
                    (status.value,),
                )
            else:
                cursor.execute("SELECT * FROM change_authorizations ORDER BY issued_at DESC")
            return [self._row_to_authorization(r) for r in cursor.fetchall()]

    def _row_to_authorization(self, row: sqlite3.Row) -> ChangeAuthorization:
        return ChangeAuthorization(
            authorization_id=row["authorization_id"],
            approval_request_id=row["approval_request_id"],
            decision_id=row["decision_id"],
            authorized_change_type=RecommendationType(row["authorized_change_type"]),
            authorized_subject=row["authorized_subject"],
            authorized_version=row["authorized_version"],
            authorized_commit_sha=row["authorized_commit_sha"],
            authorization_scope=row["authorization_scope"],
            evidence_package_id=row["evidence_package_id"],
            evidence_package_hash=row["evidence_package_hash"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            status=AuthorizationStatus(row["status"]),
        )

    # --- Approval Policies ---

    def save_policy(self, policy: ApprovalPolicy) -> ApprovalPolicy:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO approval_policies (
                    policy_id, name, change_type, risk_level, required_approvals,
                    required_evidence, required_verifications, human_role_requirements,
                    enabled, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy.policy_id,
                    policy.name,
                    policy.change_type.value,
                    policy.risk_level.value,
                    policy.required_approvals,
                    json.dumps(policy.required_evidence),
                    json.dumps(policy.required_verifications),
                    json.dumps(policy.human_role_requirements),
                    1 if policy.enabled else 0,
                    policy.version,
                ),
            )
            conn.commit()
        return policy

    def get_policy(self, policy_id: str) -> Optional[ApprovalPolicy]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approval_policies WHERE policy_id = ?", (policy_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_policy(row)

    def list_policies(self) -> List[ApprovalPolicy]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM approval_policies WHERE enabled = 1")
            return [self._row_to_policy(r) for r in cursor.fetchall()]

    def _row_to_policy(self, row: sqlite3.Row) -> ApprovalPolicy:
        return ApprovalPolicy(
            policy_id=row["policy_id"],
            name=row["name"],
            change_type=RecommendationType(row["change_type"]),
            risk_level=RiskLevel(row["risk_level"]),
            required_approvals=row["required_approvals"],
            required_evidence=json.loads(row["required_evidence"] or "[]"),
            required_verifications=json.loads(row["required_verifications"] or "[]"),
            human_role_requirements=json.loads(row["human_role_requirements"] or "[]"),
            enabled=bool(row["enabled"]),
            version=row["version"],
        )

    # --- Audit Trail ---

    def append_audit_record(self, record: GovernanceAuditRecord) -> GovernanceAuditRecord:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO governance_audit (
                    event_id, event_type, actor_type, actor_id, subject_type,
                    subject_id, previous_state, new_state, timestamp,
                    evidence_package_id, approval_request_id, authorization_id,
                    content_hash, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.event_id,
                    record.event_type,
                    record.actor_type.value,
                    record.actor_id,
                    record.subject_type,
                    record.subject_id,
                    record.previous_state,
                    record.new_state,
                    record.timestamp,
                    record.evidence_package_id,
                    record.approval_request_id,
                    record.authorization_id,
                    record.content_hash,
                    json.dumps(record.details),
                ),
            )
            conn.commit()
        return record

    def list_audit_records(
        self,
        subject_id: Optional[str] = None,
        approval_request_id: Optional[str] = None,
    ) -> List[GovernanceAuditRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if subject_id:
                cursor.execute(
                    "SELECT * FROM governance_audit WHERE subject_id = ? ORDER BY timestamp DESC",
                    (subject_id,),
                )
            elif approval_request_id:
                cursor.execute(
                    "SELECT * FROM governance_audit WHERE approval_request_id = ? ORDER BY timestamp DESC",
                    (approval_request_id,),
                )
            else:
                cursor.execute("SELECT * FROM governance_audit ORDER BY timestamp DESC")
            return [self._row_to_audit(r) for r in cursor.fetchall()]

    def _row_to_audit(self, row: sqlite3.Row) -> GovernanceAuditRecord:
        return GovernanceAuditRecord(
            event_id=row["event_id"],
            event_type=row["event_type"],
            actor_type=ActorType(row["actor_type"]),
            actor_id=row["actor_id"],
            subject_type=row["subject_type"],
            subject_id=row["subject_id"],
            previous_state=row["previous_state"],
            new_state=row["new_state"],
            timestamp=row["timestamp"],
            evidence_package_id=row["evidence_package_id"],
            approval_request_id=row["approval_request_id"],
            authorization_id=row["authorization_id"],
            content_hash=row["content_hash"],
            details=json.loads(row["details"] or "{}"),
        )
