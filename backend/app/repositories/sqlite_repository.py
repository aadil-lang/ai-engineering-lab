import json
import sqlite3
from typing import Any
from backend.app.core.database import get_db_cursor, init_db
from backend.app.models.enums import ExecutionSource, CampaignStatus, CampaignType
from backend.app.models.campaign import Campaign, CampaignConfiguration
from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.metric import Metric
from backend.app.models.assessment import Assessment, DimensionScore
from backend.app.models.test_action import TestAction
from backend.app.models.diagnosis import (
    EngineeringDiagnosis,
    DeterministicSignal,
    ReproductionStep,
    DiagnosisClaim,
)
from backend.app.models.remediation import (
    RemediationTask,
    CodeChange,
    FileChange,
    RemediationAttempt,
    RegressionVerification,
)
from backend.app.models.reliability import PredictionRecord
from backend.app.repositories.base import (
    RunRepositoryInterface,
    TargetRepositoryInterface,
    TestCaseRepositoryInterface,
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    MetricRepositoryInterface,
    AssessmentRepositoryInterface,
    DiagnosisRepositoryInterface,
    RemediationRepositoryInterface,
    PredictionRecordRepositoryInterface,
    CampaignRepositoryInterface,
)

class SQLiteRepository(
    RunRepositoryInterface,
    TargetRepositoryInterface,
    TestCaseRepositoryInterface,
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    MetricRepositoryInterface,
    AssessmentRepositoryInterface,
    DiagnosisRepositoryInterface,
    RemediationRepositoryInterface,
    PredictionRecordRepositoryInterface,
    CampaignRepositoryInterface,
):

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        init_db(self.db_path)

    # ------------------ Run Repository ------------------
    def create_run(self, run: TestRun) -> TestRun:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("PRAGMA table_info(test_runs);")
            cols = [r[1] for r in cursor.fetchall()]
            camp_type_val = run.campaign_type.value if hasattr(run.campaign_type, 'value') else (str(run.campaign_type) if run.campaign_type else "REAL_RELIABILITY")
            if "campaign_type" in cols and "campaign_id" in cols:
                cursor.execute(
                    """
                    INSERT INTO test_runs (
                        run_id, application_id, application_version, test_mode, runner_type,
                        test_case_id, status, started_at, finished_at, duration_ms,
                        environment_id, browser_context_id, session_id,
                        natural_language_goal, max_agent_steps, agent_thought_trace_json,
                        actions_json, evidence_ids_json, failure_ids_json,
                        metrics_summary_json, logs_json, created_at,
                        execution_source, feature_vector_version, campaign_id, campaign_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.application_id,
                        run.application_version,
                        run.test_mode.value,
                        run.runner_type.value if hasattr(run.runner_type, 'value') else str(run.runner_type),
                        run.test_case_id,
                        run.status.value,
                        run.started_at,
                        run.finished_at,
                        run.duration_ms,
                        run.environment_id,
                        run.browser_context_id,
                        run.session_id,
                        run.natural_language_goal,
                        run.max_agent_steps,
                        json.dumps(run.agent_thought_trace),
                        json.dumps([a.model_dump() for a in run.actions]),
                        json.dumps(run.evidence_ids),
                        json.dumps(run.failure_ids),
                        json.dumps(run.metrics_summary),
                        json.dumps(run.logs),
                        run.created_at,
                        run.execution_source.value if hasattr(run.execution_source, 'value') else str(run.execution_source),
                        run.feature_vector_version,
                        run.campaign_id,
                        camp_type_val,
                    ),
                )
            elif "campaign_id" in cols:
                cursor.execute(
                    """
                    INSERT INTO test_runs (
                        run_id, application_id, application_version, test_mode, runner_type,
                        test_case_id, status, started_at, finished_at, duration_ms,
                        environment_id, browser_context_id, session_id,
                        natural_language_goal, max_agent_steps, agent_thought_trace_json,
                        actions_json, evidence_ids_json, failure_ids_json,
                        metrics_summary_json, logs_json, created_at,
                        execution_source, feature_vector_version, campaign_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.application_id,
                        run.application_version,
                        run.test_mode.value,
                        run.runner_type.value if hasattr(run.runner_type, 'value') else str(run.runner_type),
                        run.test_case_id,
                        run.status.value,
                        run.started_at,
                        run.finished_at,
                        run.duration_ms,
                        run.environment_id,
                        run.browser_context_id,
                        run.session_id,
                        run.natural_language_goal,
                        run.max_agent_steps,
                        json.dumps(run.agent_thought_trace),
                        json.dumps([a.model_dump() for a in run.actions]),
                        json.dumps(run.evidence_ids),
                        json.dumps(run.failure_ids),
                        json.dumps(run.metrics_summary),
                        json.dumps(run.logs),
                        run.created_at,
                        run.execution_source.value if hasattr(run.execution_source, 'value') else str(run.execution_source),
                        run.feature_vector_version,
                        run.campaign_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO test_runs (
                        run_id, application_id, application_version, test_mode, runner_type,
                        test_case_id, status, started_at, finished_at, duration_ms,
                        environment_id, browser_context_id, session_id,
                        natural_language_goal, max_agent_steps, agent_thought_trace_json,
                        actions_json, evidence_ids_json, failure_ids_json,
                        metrics_summary_json, logs_json, created_at,
                        execution_source, feature_vector_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run.run_id,
                        run.application_id,
                        run.application_version,
                        run.test_mode.value,
                        run.runner_type.value if hasattr(run.runner_type, 'value') else str(run.runner_type),
                        run.test_case_id,
                        run.status.value,
                        run.started_at,
                        run.finished_at,
                        run.duration_ms,
                        run.environment_id,
                        run.browser_context_id,
                        run.session_id,
                        run.natural_language_goal,
                        run.max_agent_steps,
                        json.dumps(run.agent_thought_trace),
                        json.dumps([a.model_dump() for a in run.actions]),
                        json.dumps(run.evidence_ids),
                        json.dumps(run.failure_ids),
                        json.dumps(run.metrics_summary),
                        json.dumps(run.logs),
                        run.created_at,
                        run.execution_source.value if hasattr(run.execution_source, 'value') else str(run.execution_source),
                        run.feature_vector_version,
                    ),
                )
        return run


    def get_run(self, run_id: str) -> TestRun | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM test_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def update_run(self, run: TestRun) -> TestRun:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                UPDATE test_runs SET
                    status = ?,
                    finished_at = ?,
                    duration_ms = ?,
                    agent_thought_trace_json = ?,
                    actions_json = ?,
                    evidence_ids_json = ?,
                    failure_ids_json = ?,
                    metrics_summary_json = ?,
                    logs_json = ?,
                    execution_source = ?,
                    feature_vector_version = ?
                WHERE run_id = ?
                """,
                (
                    run.status.value,
                    run.finished_at,
                    run.duration_ms,
                    json.dumps(run.agent_thought_trace),
                    json.dumps([a.model_dump() for a in run.actions]),
                    json.dumps(run.evidence_ids),
                    json.dumps(run.failure_ids),
                    json.dumps(run.metrics_summary),
                    json.dumps(run.logs),
                    run.execution_source.value if hasattr(run.execution_source, 'value') else str(run.execution_source),
                    run.feature_vector_version,
                    run.run_id,
                ),
            )
        return run

    def list_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        application_id: str | None = None,
        test_mode: str | None = None,
        status: str | None = None,
        campaign_id: str | None = None,
    ) -> list[TestRun]:
        query = "SELECT * FROM test_runs WHERE 1=1"
        params: list[Any] = []
        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        if test_mode:
            query += " AND test_mode = ?"
            params.append(test_mode)
        if status:
            query += " AND status = ?"
            params.append(status)
        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_run(r) for r in rows]

    def count_runs(
        self,
        application_id: str | None = None,
        test_mode: str | None = None,
        status: str | None = None,
        campaign_id: str | None = None,
    ) -> int:
        query = "SELECT COUNT(*) FROM test_runs WHERE 1=1"
        params: list[Any] = []
        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        if test_mode:
            query += " AND test_mode = ?"
            params.append(test_mode)
        if status:
            query += " AND status = ?"
            params.append(status)
        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def _row_to_run(self, row: sqlite3.Row) -> TestRun:
        actions_data = json.loads(row["actions_json"]) if row["actions_json"] else []
        actions = [TestAction(**a) for a in actions_data]
        keys = row.keys()
        runner_type_val = row["runner_type"] if "runner_type" in keys and row["runner_type"] else "MOCK"
        browser_context_id = row["browser_context_id"] if "browser_context_id" in keys else None
        session_id = row["session_id"] if "session_id" in keys else None
        natural_language_goal = row["natural_language_goal"] if "natural_language_goal" in keys else None
        max_agent_steps = row["max_agent_steps"] if "max_agent_steps" in keys and row["max_agent_steps"] is not None else 10
        agent_thought_trace = json.loads(row["agent_thought_trace_json"]) if "agent_thought_trace_json" in keys and row["agent_thought_trace_json"] else []
        campaign_id = row["campaign_id"] if "campaign_id" in keys else None
        raw_camp_type = row["campaign_type"] if "campaign_type" in keys and row["campaign_type"] else "REAL_RELIABILITY"
        try:
            campaign_type = CampaignType(raw_camp_type)
        except ValueError:
            campaign_type = CampaignType.REAL_RELIABILITY
        
        raw_exec_source = row["execution_source"] if "execution_source" in keys and row["execution_source"] else "UNKNOWN"
        try:
            exec_source = ExecutionSource(raw_exec_source)
        except ValueError:
            exec_source = ExecutionSource.UNKNOWN
        fv_version = row["feature_vector_version"] if "feature_vector_version" in keys and row["feature_vector_version"] else "v1.0-temporal"

        return TestRun(
            run_id=row["run_id"],
            application_id=row["application_id"],
            application_version=row["application_version"],
            test_mode=row["test_mode"],
            runner_type=runner_type_val,
            execution_source=exec_source,
            test_case_id=row["test_case_id"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            duration_ms=row["duration_ms"] or 0,
            environment_id=row["environment_id"] or "env_default",
            browser_context_id=browser_context_id,
            session_id=session_id,
            natural_language_goal=natural_language_goal,
            max_agent_steps=max_agent_steps,
            agent_thought_trace=agent_thought_trace,
            actions=actions,
            evidence_ids=json.loads(row["evidence_ids_json"]) if row["evidence_ids_json"] else [],
            failure_ids=json.loads(row["failure_ids_json"]) if row["failure_ids_json"] else [],
            metrics_summary=json.loads(row["metrics_summary_json"]) if row["metrics_summary_json"] else {},
            logs=json.loads(row["logs_json"]) if row["logs_json"] else [],
            feature_vector_version=fv_version,
            campaign_id=campaign_id,
            campaign_type=campaign_type,
            created_at=row["created_at"],
        )

    # ------------------ Target Repository ------------------
    def create_target(self, target: ApplicationTarget) -> ApplicationTarget:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("PRAGMA table_info(application_targets);")
            cols = [r[1] for r in cursor.fetchall()]
            if "application_id" in cols and "application_type" in cols:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO application_targets (
                        target_id, application_id, application_type, name, target_type, base_url, environment,
                        version, description, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target.target_id,
                        target.application_id or target.target_id,
                        target.application_type,
                        target.name,
                        target.target_type.value,
                        target.base_url,
                        target.environment,
                        target.version,
                        target.description,
                        json.dumps(target.metadata),
                        target.created_at,
                        target.updated_at,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO application_targets (
                        target_id, name, target_type, base_url, environment,
                        version, description, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        target.target_id,
                        target.name,
                        target.target_type.value,
                        target.base_url,
                        target.environment,
                        target.version,
                        target.description,
                        json.dumps(target.metadata),
                        target.created_at,
                        target.updated_at,
                    ),
                )
        return target

    def get_target(self, target_id: str) -> ApplicationTarget | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM application_targets WHERE target_id = ?", (target_id,))
            row = cursor.fetchone()
            if not row:
                return None
            keys = row.keys()
            app_id = row["application_id"] if "application_id" in keys and row["application_id"] else row["target_id"]
            app_type = row["application_type"] if "application_type" in keys else None
            return ApplicationTarget(
                target_id=row["target_id"],
                application_id=app_id,
                application_type=app_type,
                name=row["name"],
                target_type=row["target_type"],
                base_url=row["base_url"],
                environment=row["environment"],
                version=row["version"],
                description=row["description"] or "",
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def list_targets(self) -> list[ApplicationTarget]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM application_targets ORDER BY created_at ASC")
            rows = cursor.fetchall()
            result = []
            for r in rows:
                keys = r.keys()
                app_id = r["application_id"] if "application_id" in keys and r["application_id"] else r["target_id"]
                app_type = r["application_type"] if "application_type" in keys else None
                result.append(
                    ApplicationTarget(
                        target_id=r["target_id"],
                        application_id=app_id,
                        application_type=app_type,
                        name=r["name"],
                        target_type=r["target_type"],
                        base_url=r["base_url"],
                        environment=r["environment"],
                        version=r["version"],
                        description=r["description"] or "",
                        metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                    )
                )
            return result

    # ------------------ Test Case Repository ------------------
    def create_test_case(self, test_case: TestCase) -> TestCase:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO test_cases (
                    test_case_id, target_id, name, test_mode, description,
                    steps_json, assertions_json, tags_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_case.test_case_id,
                    test_case.target_id,
                    test_case.name,
                    test_case.test_mode.value,
                    test_case.description,
                    json.dumps(test_case.steps),
                    json.dumps(test_case.assertions),
                    json.dumps(test_case.tags),
                    test_case.created_at,
                ),
            )
        return test_case

    def get_test_case(self, test_case_id: str) -> TestCase | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM test_cases WHERE test_case_id = ?", (test_case_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return TestCase(
                test_case_id=row["test_case_id"],
                target_id=row["target_id"],
                name=row["name"],
                test_mode=row["test_mode"],
                description=row["description"] or "",
                steps=json.loads(row["steps_json"]) if row["steps_json"] else [],
                assertions=json.loads(row["assertions_json"]) if row["assertions_json"] else [],
                tags=json.loads(row["tags_json"]) if row["tags_json"] else [],
                created_at=row["created_at"],
            )

    def list_test_cases(self, target_id: str | None = None, test_mode: str | None = None) -> list[TestCase]:
        query = "SELECT * FROM test_cases WHERE 1=1"
        params: list[Any] = []
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        if test_mode:
            query += " AND test_mode = ?"
            params.append(test_mode)
        query += " ORDER BY created_at ASC"

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                TestCase(
                    test_case_id=r["test_case_id"],
                    target_id=r["target_id"],
                    name=r["name"],
                    test_mode=r["test_mode"],
                    description=r["description"] or "",
                    steps=json.loads(r["steps_json"]) if r["steps_json"] else [],
                    assertions=json.loads(r["assertions_json"]) if r["assertions_json"] else [],
                    tags=json.loads(r["tags_json"]) if r["tags_json"] else [],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # ------------------ Evidence Repository ------------------
    def save_evidence(self, evidence: Evidence) -> Evidence:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO evidence_records (
                    evidence_id, run_id, action_id, evidence_type, title,
                    artifact_path, mime_type, payload_json, metadata_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.run_id,
                    evidence.action_id,
                    evidence.evidence_type.value if hasattr(evidence.evidence_type, 'value') else str(evidence.evidence_type),
                    evidence.title,
                    evidence.artifact_path,
                    evidence.mime_type,
                    json.dumps(evidence.payload),
                    json.dumps(evidence.metadata),
                    evidence.timestamp,
                ),
            )
        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM evidence_records WHERE evidence_id = ?", (evidence_id,))
            row = cursor.fetchone()
            if not row:
                return None
            keys = row.keys()
            artifact_path = row["artifact_path"] if "artifact_path" in keys else None
            mime_type = row["mime_type"] if "mime_type" in keys and row["mime_type"] else "application/json"
            return Evidence(
                evidence_id=row["evidence_id"],
                run_id=row["run_id"],
                action_id=row["action_id"],
                evidence_type=row["evidence_type"],
                title=row["title"],
                artifact_path=artifact_path,
                mime_type=mime_type,
                payload=json.loads(row["payload_json"]) if row["payload_json"] else {},
                metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                timestamp=row["timestamp"],
            )

    def get_evidence_by_run(self, run_id: str) -> list[Evidence]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM evidence_records WHERE run_id = ? ORDER BY timestamp ASC", (run_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                keys = r.keys()
                artifact_path = r["artifact_path"] if "artifact_path" in keys else None
                mime_type = r["mime_type"] if "mime_type" in keys and r["mime_type"] else "application/json"
                result.append(
                    Evidence(
                        evidence_id=r["evidence_id"],
                        run_id=r["run_id"],
                        action_id=r["action_id"],
                        evidence_type=r["evidence_type"],
                        title=r["title"],
                        artifact_path=artifact_path,
                        mime_type=mime_type,
                        payload=json.loads(r["payload_json"]) if r["payload_json"] else {},
                        metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                        timestamp=r["timestamp"],
                    )
                )
            return result

    def list_evidence(self, limit: int = 1000, offset: int = 0) -> list[Evidence]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM evidence_records ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                keys = r.keys()
                artifact_path = r["artifact_path"] if "artifact_path" in keys else None
                mime_type = r["mime_type"] if "mime_type" in keys else None
                result.append(
                    Evidence(
                        evidence_id=r["evidence_id"],
                        run_id=r["run_id"],
                        action_id=r["action_id"],
                        evidence_type=r["evidence_type"],
                        title=r["title"],
                        artifact_path=artifact_path,
                        mime_type=r["mime_type"] if "mime_type" in keys and r["mime_type"] else "application/json",
                        payload=json.loads(r["payload_json"]) if r["payload_json"] else {},
                        metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                        timestamp=r["timestamp"],
                    )
                )
            return result

    # ------------------ Failure Repository ------------------
    def save_failure(self, failure: Failure) -> Failure:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO failure_records (
                    failure_id, run_id, action_id, category, severity,
                    title, message, stack_trace, suggested_remediation,
                    failed_action, selector, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    failure.failure_id,
                    failure.run_id,
                    failure.action_id,
                    failure.category.value,
                    failure.severity.value,
                    failure.title,
                    failure.message,
                    failure.stack_trace,
                    failure.suggested_remediation,
                    failure.failed_action,
                    failure.selector,
                    failure.timestamp,
                ),
            )
        return failure

    def get_failure(self, failure_id: str) -> Failure | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM failure_records WHERE failure_id = ?", (failure_id,))
            row = cursor.fetchone()
            if not row:
                return None
            keys = row.keys()
            return Failure(
                failure_id=row["failure_id"],
                run_id=row["run_id"],
                action_id=row["action_id"],
                category=row["category"],
                severity=row["severity"],
                title=row["title"],
                message=row["message"],
                stack_trace=row["stack_trace"],
                suggested_remediation=row["suggested_remediation"],
                failed_action=row["failed_action"] if "failed_action" in keys else None,
                selector=row["selector"] if "selector" in keys else None,
                timestamp=row["timestamp"],
            )

    def get_failures_by_run(self, run_id: str) -> list[Failure]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM failure_records WHERE run_id = ? ORDER BY timestamp ASC", (run_id,))
            rows = cursor.fetchall()
            failures = []
            for r in rows:
                keys = r.keys()
                failures.append(
                    Failure(
                        failure_id=r["failure_id"],
                        run_id=r["run_id"],
                        action_id=r["action_id"],
                        category=r["category"],
                        severity=r["severity"],
                        title=r["title"],
                        message=r["message"],
                        stack_trace=r["stack_trace"],
                        suggested_remediation=r["suggested_remediation"],
                        failed_action=r["failed_action"] if "failed_action" in keys else None,
                        selector=r["selector"] if "selector" in keys else None,
                        timestamp=r["timestamp"],
                    )
                )
            return failures

    def list_failures(self, limit: int = 1000, offset: int = 0) -> list[Failure]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM failure_records ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            failures = []
            for r in rows:
                keys = r.keys()
                failures.append(
                    Failure(
                        failure_id=r["failure_id"],
                        run_id=r["run_id"],
                        action_id=r["action_id"],
                        category=r["category"],
                        severity=r["severity"],
                        title=r["title"],
                        message=r["message"],
                        stack_trace=r["stack_trace"],
                        suggested_remediation=r["suggested_remediation"],
                        failed_action=r["failed_action"] if "failed_action" in keys else None,
                        selector=r["selector"] if "selector" in keys else None,
                        timestamp=r["timestamp"],
                    )
                )
            return failures

    # ------------------ Metric Repository ------------------
    def save_metric(self, metric: Metric) -> Metric:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO metrics_records (
                    metric_id, run_id, name, value, unit, tags_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metric.metric_id,
                    metric.run_id,
                    metric.name,
                    metric.value,
                    metric.unit,
                    json.dumps(metric.tags),
                    metric.timestamp,
                ),
            )
        return metric

    def get_metrics_by_run(self, run_id: str) -> list[Metric]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM metrics_records WHERE run_id = ? ORDER BY timestamp ASC", (run_id,))
            rows = cursor.fetchall()
            return [
                Metric(
                    metric_id=r["metric_id"],
                    run_id=r["run_id"],
                    name=r["name"],
                    value=r["value"],
                    unit=r["unit"],
                    tags=json.loads(r["tags_json"]) if r["tags_json"] else {},
                    timestamp=r["timestamp"],
                )
                for r in rows
            ]

    # ------------------ Assessment Repository ------------------
    def save_assessment(self, assessment: Assessment) -> Assessment:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO assessment_records (
                    assessment_id, application_id, overall_score, status,
                    dimensions_json, findings_ids_json, recommendations_json,
                    started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment.assessment_id,
                    assessment.application_id,
                    assessment.overall_score,
                    assessment.status,
                    json.dumps([d.model_dump() for d in assessment.dimensions]),
                    json.dumps(assessment.findings_ids),
                    json.dumps(assessment.recommendations),
                    assessment.started_at,
                    assessment.finished_at,
                ),
            )
        return assessment

    def get_assessment(self, assessment_id: str) -> Assessment | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM assessment_records WHERE assessment_id = ?", (assessment_id,))
            row = cursor.fetchone()
            if not row:
                return None
            dims = [DimensionScore(**d) for d in json.loads(row["dimensions_json"])] if row["dimensions_json"] else []
            return Assessment(
                assessment_id=row["assessment_id"],
                application_id=row["application_id"],
                overall_score=row["overall_score"],
                status=row["status"],
                dimensions=dims,
                findings_ids=json.loads(row["findings_ids_json"]) if row["findings_ids_json"] else [],
                recommendations=json.loads(row["recommendations_json"]) if row["recommendations_json"] else [],
                started_at=row["started_at"],
                finished_at=row["finished_at"],
            )

    def list_assessments(self, application_id: str | None = None) -> list[Assessment]:
        query = "SELECT * FROM assessment_records WHERE 1=1"
        params: list[Any] = []
        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        query += " ORDER BY started_at DESC"

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                Assessment(
                    assessment_id=r["assessment_id"],
                    application_id=r["application_id"],
                    overall_score=r["overall_score"],
                    status=r["status"],
                    dimensions=[DimensionScore(**d) for d in json.loads(r["dimensions_json"])] if r["dimensions_json"] else [],
                    findings_ids=json.loads(r["findings_ids_json"]) if r["findings_ids_json"] else [],
                    recommendations=json.loads(r["recommendations_json"]) if r["recommendations_json"] else [],
                    started_at=r["started_at"],
                    finished_at=r["finished_at"],
                )
                for r in rows
            ]

    # ------------------ Diagnosis Repository ------------------
    def save_diagnosis(self, diagnosis: EngineeringDiagnosis) -> EngineeringDiagnosis:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO engineering_diagnoses (
                    diagnosis_id, run_id, failure_id, title, root_cause_summary,
                    failure_category, confidence_score, suspected_component,
                    deterministic_signals_json, reproduction_steps_json,
                    suggested_fix, code_diff_suggestion, regression_test_spec,
                    severity, evidence_bundle_summary, claims_json, grounding_score,
                    is_grounded, grounded_root_cause, grounded_suspected_component,
                    grounded_confidence_score, validation_notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    diagnosis.diagnosis_id,
                    diagnosis.run_id,
                    diagnosis.failure_id,
                    diagnosis.title,
                    diagnosis.root_cause_summary,
                    diagnosis.failure_category.value if hasattr(diagnosis.failure_category, 'value') else str(diagnosis.failure_category),
                    diagnosis.confidence_score,
                    diagnosis.suspected_component,
                    json.dumps([s.model_dump() for s in diagnosis.deterministic_signals]),
                    json.dumps([r.model_dump() for r in diagnosis.reproduction_steps]),
                    diagnosis.suggested_fix,
                    diagnosis.code_diff_suggestion,
                    diagnosis.regression_test_spec,
                    diagnosis.severity.value if hasattr(diagnosis.severity, 'value') else str(diagnosis.severity),
                    diagnosis.evidence_bundle_summary,
                    json.dumps([c.model_dump() for c in diagnosis.claims]),
                    diagnosis.grounding_score,
                    1 if diagnosis.is_grounded else 0,
                    diagnosis.grounded_root_cause,
                    diagnosis.grounded_suspected_component,
                    diagnosis.grounded_confidence_score,
                    json.dumps(diagnosis.validation_notes),
                    diagnosis.created_at,
                ),
            )
        return diagnosis

    def get_diagnosis(self, diagnosis_id: str) -> EngineeringDiagnosis | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM engineering_diagnoses WHERE diagnosis_id = ?", (diagnosis_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_diagnosis(row)

    def get_diagnosis_by_run(self, run_id: str) -> EngineeringDiagnosis | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM engineering_diagnoses WHERE run_id = ? ORDER BY created_at DESC LIMIT 1", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_diagnosis(row)

    def list_diagnoses(self, limit: int = 50, offset: int = 0) -> list[EngineeringDiagnosis]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM engineering_diagnoses ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_diagnosis(r) for r in rows]

    def _row_to_diagnosis(self, row: sqlite3.Row) -> EngineeringDiagnosis:
        keys = row.keys()
        signals_data = json.loads(row["deterministic_signals_json"]) if row["deterministic_signals_json"] else []
        repro_data = json.loads(row["reproduction_steps_json"]) if row["reproduction_steps_json"] else []
        
        claims_data = []
        if "claims_json" in keys and row["claims_json"]:
            try:
                claims_data = json.loads(row["claims_json"])
            except Exception:
                claims_data = []

        validation_notes = []
        if "validation_notes_json" in keys and row["validation_notes_json"]:
            try:
                validation_notes = json.loads(row["validation_notes_json"])
            except Exception:
                validation_notes = []

        grounding_score = row["grounding_score"] if "grounding_score" in keys and row["grounding_score"] is not None else 1.0
        is_grounded = bool(row["is_grounded"]) if "is_grounded" in keys and row["is_grounded"] is not None else True
        grounded_rc = row["grounded_root_cause"] if "grounded_root_cause" in keys else None
        grounded_comp = row["grounded_suspected_component"] if "grounded_suspected_component" in keys else None
        grounded_conf = row["grounded_confidence_score"] if "grounded_confidence_score" in keys else None

        return EngineeringDiagnosis(
            diagnosis_id=row["diagnosis_id"],
            run_id=row["run_id"],
            failure_id=row["failure_id"],
            title=row["title"],
            root_cause_summary=row["root_cause_summary"],
            failure_category=row["failure_category"],
            confidence_score=row["confidence_score"] if row["confidence_score"] is not None else 0.9,
            suspected_component=row["suspected_component"],
            deterministic_signals=[DeterministicSignal(**s) for s in signals_data],
            reproduction_steps=[ReproductionStep(**r) for r in repro_data],
            suggested_fix=row["suggested_fix"],
            code_diff_suggestion=row["code_diff_suggestion"],
            regression_test_spec=row["regression_test_spec"],
            severity=row["severity"],
            evidence_bundle_summary=row["evidence_bundle_summary"] or "",
            claims=[DiagnosisClaim(**c) for c in claims_data],
            grounding_score=grounding_score,
            is_grounded=is_grounded,
            grounded_root_cause=grounded_rc,
            grounded_suspected_component=grounded_comp,
            grounded_confidence_score=grounded_conf,
            validation_notes=validation_notes,
            created_at=row["created_at"],
        )

    # ------------------ Remediation Repository ------------------
    def save_remediation_task(self, task: RemediationTask) -> RemediationTask:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO remediation_tasks (
                    task_id, run_id, diagnosis_id, status, target_repository,
                    target_branch, base_commit, code_changes_json, attempts_json,
                    verifications_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    task.run_id,
                    task.diagnosis_id,
                    task.status.value if hasattr(task.status, 'value') else str(task.status),
                    task.target_repository,
                    task.target_branch,
                    task.base_commit,
                    json.dumps([c.model_dump() for c in task.code_changes]),
                    json.dumps([a.model_dump() for a in task.attempts]),
                    json.dumps([v.model_dump() for v in task.verifications]),
                    task.created_at,
                    task.updated_at,
                ),
            )
        return task

    def get_remediation_task(self, task_id: str) -> RemediationTask | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM remediation_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_remediation_task(row)

    def get_remediation_tasks_by_run(self, run_id: str) -> list[RemediationTask]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM remediation_tasks WHERE run_id = ? ORDER BY created_at DESC", (run_id,))
            rows = cursor.fetchall()
            return [self._row_to_remediation_task(r) for r in rows]

    def list_remediation_tasks(self, limit: int = 50, offset: int = 0) -> list[RemediationTask]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM remediation_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            return [self._row_to_remediation_task(r) for r in rows]

    def _row_to_remediation_task(self, row: sqlite3.Row) -> RemediationTask:
        code_changes_data = json.loads(row["code_changes_json"]) if row["code_changes_json"] else []
        attempts_data = json.loads(row["attempts_json"]) if row["attempts_json"] else []
        verifications_data = json.loads(row["verifications_json"]) if row["verifications_json"] else []

        code_changes = []
        for c in code_changes_data:
            files = [FileChange(**f) for f in c.get("files", [])]
            c_copy = dict(c)
            c_copy["files"] = files
            code_changes.append(CodeChange(**c_copy))

        attempts = [RemediationAttempt(**a) for a in attempts_data]
        verifications = [RegressionVerification(**v) for v in verifications_data]

        return RemediationTask(
            task_id=row["task_id"],
            run_id=row["run_id"],
            diagnosis_id=row["diagnosis_id"],
            status=row["status"],
            target_repository=row["target_repository"],
            target_branch=row["target_branch"],
            base_commit=row["base_commit"],
            code_changes=code_changes,
            attempts=attempts,
            verifications=verifications,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ------------------ Prediction Record Repository ------------------
    def save_prediction_record(self, record: PredictionRecord) -> PredictionRecord:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO prediction_records (
                    prediction_id, test_case_id, test_case_name, feature_run_id,
                    predicted_failure_probability, predicted_risk_band,
                    prediction_class, model_version, feature_vector_version,
                    prediction_timestamp, target_run_id, actual_outcome,
                    is_correct, evaluation_status, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.prediction_id,
                    record.test_case_id,
                    record.test_case_name,
                    record.feature_run_id,
                    record.predicted_failure_probability,
                    record.predicted_risk_band.value if hasattr(record.predicted_risk_band, 'value') else str(record.predicted_risk_band),
                    record.prediction_class,
                    record.model_version,
                    record.feature_vector_version,
                    record.prediction_timestamp,
                    record.target_run_id,
                    record.actual_outcome,
                    1 if record.is_correct is True else (0 if record.is_correct is False else None),
                    record.evaluation_status.value if hasattr(record.evaluation_status, 'value') else str(record.evaluation_status),
                    record.evaluated_at,
                ),
            )
        return record

    def get_prediction_record(self, prediction_id: str) -> PredictionRecord | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM prediction_records WHERE prediction_id = ?", (prediction_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_prediction_record(row)

    def list_prediction_records(
        self,
        test_case_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[PredictionRecord]:
        query = "SELECT * FROM prediction_records WHERE 1=1"
        params: list[Any] = []
        if test_case_id:
            query += " AND test_case_id = ?"
            params.append(test_case_id)
        if status:
            query += " AND evaluation_status = ?"
            params.append(status)
        query += " ORDER BY prediction_timestamp DESC LIMIT ?"
        params.append(limit)

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_prediction_record(r) for r in rows]

    def update_prediction_record(self, record: PredictionRecord) -> PredictionRecord:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                UPDATE prediction_records SET
                    target_run_id = ?,
                    actual_outcome = ?,
                    is_correct = ?,
                    evaluation_status = ?,
                    evaluated_at = ?
                WHERE prediction_id = ?
                """,
                (
                    record.target_run_id,
                    record.actual_outcome,
                    1 if record.is_correct is True else (0 if record.is_correct is False else None),
                    record.evaluation_status.value if hasattr(record.evaluation_status, 'value') else str(record.evaluation_status),
                    record.evaluated_at,
                    record.prediction_id,
                ),
            )
        return record

    def get_pending_predictions_for_test_case(self, test_case_id: str) -> list[PredictionRecord]:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                "SELECT * FROM prediction_records WHERE test_case_id = ? AND evaluation_status = 'PENDING' ORDER BY prediction_timestamp ASC",
                (test_case_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_prediction_record(r) for r in rows]

    def _row_to_prediction_record(self, row: sqlite3.Row) -> PredictionRecord:
        is_corr = bool(row["is_correct"]) if row["is_correct"] is not None else None
        return PredictionRecord(
            prediction_id=row["prediction_id"],
            test_case_id=row["test_case_id"],
            test_case_name=row["test_case_name"],
            feature_run_id=row["feature_run_id"],
            predicted_failure_probability=row["predicted_failure_probability"],
            predicted_risk_band=row["predicted_risk_band"],
            prediction_class=row["prediction_class"],
            model_version=row["model_version"],
            feature_vector_version=row["feature_vector_version"],
            prediction_timestamp=row["prediction_timestamp"],
            target_run_id=row["target_run_id"],
            actual_outcome=row["actual_outcome"],
            is_correct=is_corr,
            evaluation_status=row["evaluation_status"],
            evaluated_at=row["evaluated_at"],
        )

    # ------------------ Campaign Repository ------------------
    def create_campaign(self, campaign: Campaign) -> Campaign:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("PRAGMA table_info(qa_campaigns);")
            cols = [r[1] for r in cursor.fetchall()]
            camp_type_val = campaign.campaign_type.value if hasattr(campaign.campaign_type, 'value') else str(campaign.campaign_type)
            if "campaign_type" in cols:
                cursor.execute(
                    """
                    INSERT INTO qa_campaigns (
                        campaign_id, name, description, target_id, campaign_type, environment_id, status,
                        created_at, started_at, finished_at, requested_runs, completed_runs,
                        passed_runs, failed_runs, cancelled_runs, execution_sources_json,
                        configuration_json, run_ids_json, summary_report_json,
                        created_by, configuration_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        campaign.campaign_id,
                        campaign.name,
                        campaign.description,
                        campaign.target_id,
                        camp_type_val,
                        campaign.environment_id,
                        campaign.status.value,
                        campaign.created_at,
                        campaign.started_at,
                        campaign.finished_at,
                        campaign.requested_runs,
                        campaign.completed_runs,
                        campaign.passed_runs,
                        campaign.failed_runs,
                        campaign.cancelled_runs,
                        json.dumps([s.value for s in campaign.execution_sources]),
                        json.dumps(campaign.configuration.model_dump()),
                        json.dumps(campaign.run_ids),
                        json.dumps(campaign.summary_report),
                        campaign.created_by,
                        campaign.configuration_version,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO qa_campaigns (
                        campaign_id, name, description, target_id, environment_id, status,
                        created_at, started_at, finished_at, requested_runs, completed_runs,
                        passed_runs, failed_runs, cancelled_runs, execution_sources_json,
                        configuration_json, run_ids_json, summary_report_json,
                        created_by, configuration_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        campaign.campaign_id,
                        campaign.name,
                        campaign.description,
                        campaign.target_id,
                        campaign.environment_id,
                        campaign.status.value,
                        campaign.created_at,
                        campaign.started_at,
                        campaign.finished_at,
                        campaign.requested_runs,
                        campaign.completed_runs,
                        campaign.passed_runs,
                        campaign.failed_runs,
                        campaign.cancelled_runs,
                        json.dumps([s.value for s in campaign.execution_sources]),
                        json.dumps(campaign.configuration.model_dump()),
                        json.dumps(campaign.run_ids),
                        json.dumps(campaign.summary_report),
                        campaign.created_by,
                        campaign.configuration_version,
                    ),
                )
        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT * FROM qa_campaigns WHERE campaign_id = ?", (campaign_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_campaign(row)

    def update_campaign(self, campaign: Campaign) -> Campaign:
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("PRAGMA table_info(qa_campaigns);")
            cols = [r[1] for r in cursor.fetchall()]
            camp_type_val = campaign.campaign_type.value if hasattr(campaign.campaign_type, 'value') else str(campaign.campaign_type)
            if "campaign_type" in cols:
                cursor.execute(
                    """
                    UPDATE qa_campaigns SET
                        name = ?,
                        description = ?,
                        target_id = ?,
                        campaign_type = ?,
                        environment_id = ?,
                        status = ?,
                        started_at = ?,
                        finished_at = ?,
                        requested_runs = ?,
                        completed_runs = ?,
                        passed_runs = ?,
                        failed_runs = ?,
                        cancelled_runs = ?,
                        execution_sources_json = ?,
                        configuration_json = ?,
                        run_ids_json = ?,
                        summary_report_json = ?,
                        created_by = ?,
                        configuration_version = ?
                    WHERE campaign_id = ?
                    """,
                    (
                        campaign.name,
                        campaign.description,
                        campaign.target_id,
                        camp_type_val,
                        campaign.environment_id,
                        campaign.status.value,
                        campaign.started_at,
                        campaign.finished_at,
                        campaign.requested_runs,
                        campaign.completed_runs,
                        campaign.passed_runs,
                        campaign.failed_runs,
                        campaign.cancelled_runs,
                        json.dumps([s.value for s in campaign.execution_sources]),
                        json.dumps(campaign.configuration.model_dump()),
                        json.dumps(campaign.run_ids),
                        json.dumps(campaign.summary_report),
                        campaign.created_by,
                        campaign.configuration_version,
                        campaign.campaign_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    UPDATE qa_campaigns SET
                        name = ?,
                        description = ?,
                        target_id = ?,
                        environment_id = ?,
                        status = ?,
                        started_at = ?,
                        finished_at = ?,
                        requested_runs = ?,
                        completed_runs = ?,
                        passed_runs = ?,
                        failed_runs = ?,
                        cancelled_runs = ?,
                        execution_sources_json = ?,
                        configuration_json = ?,
                        run_ids_json = ?,
                        summary_report_json = ?,
                        created_by = ?,
                        configuration_version = ?
                    WHERE campaign_id = ?
                    """,
                    (
                        campaign.name,
                        campaign.description,
                        campaign.target_id,
                        campaign.environment_id,
                        campaign.status.value,
                        campaign.started_at,
                        campaign.finished_at,
                        campaign.requested_runs,
                        campaign.completed_runs,
                        campaign.passed_runs,
                        campaign.failed_runs,
                        campaign.cancelled_runs,
                        json.dumps([s.value for s in campaign.execution_sources]),
                        json.dumps(campaign.configuration.model_dump()),
                        json.dumps(campaign.run_ids),
                        json.dumps(campaign.summary_report),
                        campaign.created_by,
                        campaign.configuration_version,
                        campaign.campaign_id,
                    ),
                )
        return campaign

    def list_campaigns(self, limit: int = 50, offset: int = 0, target_id: str | None = None) -> list[Campaign]:
        query = "SELECT * FROM qa_campaigns WHERE 1=1"
        params: list[Any] = []
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_campaign(r) for r in rows]

    def count_campaigns(self, target_id: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM qa_campaigns WHERE 1=1"
        params: list[Any] = []
        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def get_runs_by_campaign(self, campaign_id: str) -> list[TestRun]:
        return self.list_runs(limit=1000, campaign_id=campaign_id)

    def _row_to_campaign(self, row: sqlite3.Row) -> Campaign:
        keys = row.keys()
        config_data = json.loads(row["configuration_json"]) if "configuration_json" in keys and row["configuration_json"] else {}
        config = CampaignConfiguration(**config_data)

        raw_sources = json.loads(row["execution_sources_json"]) if "execution_sources_json" in keys and row["execution_sources_json"] else []
        sources = []
        for s in raw_sources:
            try:
                sources.append(ExecutionSource(s))
            except ValueError:
                sources.append(ExecutionSource.UNKNOWN)

        run_ids = json.loads(row["run_ids_json"]) if "run_ids_json" in keys and row["run_ids_json"] else []
        summary_report = json.loads(row["summary_report_json"]) if "summary_report_json" in keys and row["summary_report_json"] else {}

        raw_status = row["status"] if "status" in keys else "CREATED"
        try:
            status = CampaignStatus(raw_status)
        except ValueError:
            status = CampaignStatus.CREATED

        raw_camp_type = row["campaign_type"] if "campaign_type" in keys and row["campaign_type"] else "REAL_RELIABILITY"
        try:
            campaign_type = CampaignType(raw_camp_type)
        except ValueError:
            campaign_type = CampaignType.REAL_RELIABILITY

        return Campaign(
            campaign_id=row["campaign_id"],
            name=row["name"],
            description=row["description"],
            target_id=row["target_id"],
            campaign_type=campaign_type,
            environment_id=row["environment_id"] or "local-development",
            status=status,
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            requested_runs=row["requested_runs"] or 0,
            completed_runs=row["completed_runs"] or 0,
            passed_runs=row["passed_runs"] or 0,
            failed_runs=row["failed_runs"] or 0,
            cancelled_runs=row["cancelled_runs"] or 0,
            execution_sources=sources,
            configuration=config,
            run_ids=run_ids,
            summary_report=summary_report,
            created_by=row["created_by"] or "system",
            configuration_version=row["configuration_version"] or "v1.0",
        )




