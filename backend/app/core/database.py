import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from backend.app.core.config import settings

def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.DATABASE_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db_cursor(db_path: str | None = None):
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str | None = None):
    """Initialize database tables for runs, targets, test cases, evidence, failures, and metrics."""
    with get_db_cursor(db_path) as cursor:
        # Targets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_targets (
                target_id TEXT PRIMARY KEY,
                application_id TEXT,
                application_type TEXT,
                name TEXT NOT NULL,
                target_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                environment TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        
        # Test Cases Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                test_case_id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                name TEXT NOT NULL,
                test_mode TEXT NOT NULL,
                description TEXT,
                steps_json TEXT NOT NULL,
                assertions_json TEXT,
                tags_json TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # Test Runs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                run_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                application_version TEXT NOT NULL,
                test_mode TEXT NOT NULL,
                runner_type TEXT DEFAULT 'MOCK',
                execution_source TEXT DEFAULT 'UNKNOWN',
                test_case_id TEXT,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                duration_ms INTEGER,
                environment_id TEXT,
                browser_context_id TEXT,
                session_id TEXT,
                actions_json TEXT NOT NULL,
                evidence_ids_json TEXT NOT NULL,
                failure_ids_json TEXT NOT NULL,
                metrics_summary_json TEXT,
                logs_json TEXT,
                feature_vector_version TEXT DEFAULT 'v1.0-temporal',
                created_at TEXT NOT NULL
            );
        """)

        
        # Evidence Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_records (
                evidence_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                action_id TEXT,
                evidence_type TEXT NOT NULL,
                title TEXT NOT NULL,
                artifact_path TEXT,
                mime_type TEXT DEFAULT 'application/json',
                payload_json TEXT NOT NULL,
                metadata_json TEXT,
                timestamp TEXT NOT NULL
            );
        """)

        # Failures Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_records (
                failure_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                action_id TEXT,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                stack_trace TEXT,
                suggested_remediation TEXT,
                failed_action TEXT,
                selector TEXT,
                timestamp TEXT NOT NULL
            );
        """)
        
        # Metrics Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics_records (
                metric_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                tags_json TEXT,
                timestamp TEXT NOT NULL
            );
        """)

        # Assessment Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessment_records (
                assessment_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                status TEXT NOT NULL,
                dimensions_json TEXT NOT NULL,
                findings_ids_json TEXT NOT NULL,
                recommendations_json TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT
            );
        """)

        # Engineering Diagnoses Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engineering_diagnoses (
                diagnosis_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                failure_id TEXT,
                title TEXT NOT NULL,
                root_cause_summary TEXT NOT NULL,
                failure_category TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                suspected_component TEXT NOT NULL,
                deterministic_signals_json TEXT NOT NULL,
                reproduction_steps_json TEXT NOT NULL,
                suggested_fix TEXT NOT NULL,
                code_diff_suggestion TEXT,
                regression_test_spec TEXT NOT NULL,
                severity TEXT NOT NULL,
                evidence_bundle_summary TEXT,
                claims_json TEXT,
                grounding_score REAL DEFAULT 1.0,
                is_grounded INTEGER DEFAULT 1,
                grounded_root_cause TEXT,
                grounded_suspected_component TEXT,
                grounded_confidence_score REAL,
                validation_notes_json TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Safe schema migrations for existing SQLite databases
        for col_def in [
            ("test_runs", "runner_type", "TEXT DEFAULT 'MOCK'"),
            ("test_runs", "browser_context_id", "TEXT"),
            ("test_runs", "session_id", "TEXT"),
            ("test_runs", "natural_language_goal", "TEXT"),
            ("test_runs", "max_agent_steps", "INTEGER DEFAULT 10"),
            ("test_runs", "agent_thought_trace_json", "TEXT"),
            ("evidence_records", "artifact_path", "TEXT"),
            ("evidence_records", "mime_type", "TEXT DEFAULT 'application/json'"),
            ("engineering_diagnoses", "claims_json", "TEXT"),
            ("engineering_diagnoses", "grounding_score", "REAL DEFAULT 1.0"),
            ("engineering_diagnoses", "is_grounded", "INTEGER DEFAULT 1"),
            ("engineering_diagnoses", "grounded_root_cause", "TEXT"),
            ("engineering_diagnoses", "grounded_suspected_component", "TEXT"),
            ("engineering_diagnoses", "grounded_confidence_score", "REAL"),
            ("engineering_diagnoses", "validation_notes_json", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {col_def[0]} ADD COLUMN {col_def[1]} {col_def[2]};")
            except Exception:
                pass # column already exists

        # Remediation Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS remediation_tasks (
                task_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                diagnosis_id TEXT NOT NULL,
                status TEXT NOT NULL,
                target_repository TEXT NOT NULL,
                target_branch TEXT NOT NULL,
                base_commit TEXT NOT NULL,
                code_changes_json TEXT NOT NULL,
                attempts_json TEXT NOT NULL,
                verifications_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Code Changes Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_changes (
                change_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                rationale TEXT NOT NULL,
                files_json TEXT NOT NULL,
                diff TEXT,
                risk_notes TEXT,
                tests_to_run_json TEXT,
                validation_results_json TEXT,
                created_at TEXT NOT NULL
            );
        """)

        # Remediation Attempts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS remediation_attempts (
                attempt_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                build_result_json TEXT,
                test_result_json TEXT,
                error_output TEXT
            );
        """)

        # Regression Verifications Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regression_verifications (
                verification_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                original_run_id TEXT NOT NULL,
                verification_run_id TEXT,
                status TEXT NOT NULL,
                failed_before INTEGER NOT NULL,
                failed_after INTEGER NOT NULL,
                regression_detected INTEGER NOT NULL,
                summary TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );
        """)

        # Prediction Records Table (Continuous Evaluation Tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_records (
                prediction_id TEXT PRIMARY KEY,
                test_case_id TEXT NOT NULL,
                test_case_name TEXT,
                feature_run_id TEXT NOT NULL,
                predicted_failure_probability REAL,
                predicted_risk_band TEXT NOT NULL,
                prediction_class INTEGER NOT NULL,
                model_version TEXT NOT NULL,
                feature_vector_version TEXT NOT NULL,
                prediction_timestamp TEXT NOT NULL,
                target_run_id TEXT,
                actual_outcome INTEGER,
                is_correct INTEGER,
                evaluation_status TEXT NOT NULL,
                evaluated_at TEXT
            );
        """)

        # QA Campaigns Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS qa_campaigns (
                campaign_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                target_id TEXT NOT NULL,
                campaign_type TEXT DEFAULT 'REAL_RELIABILITY',
                environment_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                requested_runs INTEGER NOT NULL,
                completed_runs INTEGER NOT NULL,
                passed_runs INTEGER NOT NULL,
                failed_runs INTEGER NOT NULL,
                cancelled_runs INTEGER NOT NULL,
                execution_sources_json TEXT NOT NULL,
                configuration_json TEXT NOT NULL,
                run_ids_json TEXT NOT NULL,
                summary_report_json TEXT,
                created_by TEXT DEFAULT 'system',
                configuration_version TEXT DEFAULT 'v1.0'
            );
        """)

        # Migration: Ensure execution_source and feature_vector_version columns exist in test_runs
        cursor.execute("PRAGMA table_info(test_runs);")
        run_cols = [row[1] for row in cursor.fetchall()]
        if "execution_source" not in run_cols:
            cursor.execute("ALTER TABLE test_runs ADD COLUMN execution_source TEXT DEFAULT 'UNKNOWN';")
            # Ensure historical baseline runs retain their established Slice 6.4 baseline provenance
            cursor.execute("""
                UPDATE test_runs 
                SET execution_source = 'DEMO_HARNESS' 
                WHERE (execution_source IS NULL OR execution_source = 'UNKNOWN') 
                  AND (application_id LIKE '%demo_shop%' OR test_case_id LIKE '%demo_shop%');
            """)
            cursor.execute("""
                UPDATE test_runs 
                SET execution_source = 'SYNTHETIC_MOCK' 
                WHERE (execution_source IS NULL OR execution_source = 'UNKNOWN');
            """)
        if "feature_vector_version" not in run_cols:
            cursor.execute("ALTER TABLE test_runs ADD COLUMN feature_vector_version TEXT DEFAULT 'v1.0-temporal';")
        if "campaign_id" not in run_cols:
            cursor.execute("ALTER TABLE test_runs ADD COLUMN campaign_id TEXT;")
        if "campaign_type" not in run_cols:
            cursor.execute("ALTER TABLE test_runs ADD COLUMN campaign_type TEXT DEFAULT 'REAL_RELIABILITY';")
        
        # Ensure historical runs have correct non-real campaign_type
        cursor.execute("""
            UPDATE test_runs 
            SET campaign_type = 'DEMO' 
            WHERE execution_source = 'DEMO_HARNESS' AND (campaign_type IS NULL OR campaign_type = 'REAL_RELIABILITY');
        """)
        cursor.execute("""
            UPDATE test_runs 
            SET campaign_type = 'SYNTHETIC' 
            WHERE execution_source IN ('SYNTHETIC_MOCK', 'UNKNOWN') AND (campaign_type IS NULL OR campaign_type = 'REAL_RELIABILITY');
        """)
        cursor.execute("""
            UPDATE test_runs 
            SET campaign_type = 'CONTROLLED_EXPERIMENT' 
            WHERE execution_source = 'CONTROLLED_DEFECT' AND (campaign_type IS NULL OR campaign_type = 'REAL_RELIABILITY');
        """)

        # Migration: Ensure failed_action and selector columns exist in failure_records
        cursor.execute("PRAGMA table_info(failure_records);")
        fail_cols = [row[1] for row in cursor.fetchall()]
        if "failed_action" not in fail_cols:
            cursor.execute("ALTER TABLE failure_records ADD COLUMN failed_action TEXT;")
        if "selector" not in fail_cols:
            cursor.execute("ALTER TABLE failure_records ADD COLUMN selector TEXT;")

        # Migration: Ensure campaign_type column exists in qa_campaigns
        cursor.execute("PRAGMA table_info(qa_campaigns);")
        camp_cols = [row[1] for row in cursor.fetchall()]
        if "campaign_type" not in camp_cols:
            cursor.execute("ALTER TABLE qa_campaigns ADD COLUMN campaign_type TEXT DEFAULT 'REAL_RELIABILITY';")

        # Migration: Ensure application_id and application_type exist in application_targets
        cursor.execute("PRAGMA table_info(application_targets);")
        target_cols = [row[1] for row in cursor.fetchall()]
        if "application_id" not in target_cols:
            cursor.execute("ALTER TABLE application_targets ADD COLUMN application_id TEXT;")
        if "application_type" not in target_cols:
            cursor.execute("ALTER TABLE application_targets ADD COLUMN application_type TEXT;")

        cursor.execute("""
            UPDATE application_targets
            SET application_id = 'app_eda', application_type = 'engineering_workflow'
            WHERE target_id = 'real_eda_local' AND (application_id IS NULL OR application_id = '');
        """)
        cursor.execute("""
            UPDATE application_targets
            SET application_id = 'app_inventory', application_type = 'crud_business'
            WHERE target_id = 'real_inventory_local' AND (application_id IS NULL OR application_id = '');
        """)
        cursor.execute("""
            UPDATE application_targets
            SET application_id = 'app_booking', application_type = 'stateful_workflow'
            WHERE target_id = 'real_booking_local' AND (application_id IS NULL OR application_id = '');
        """)
        cursor.execute("""
            UPDATE application_targets
            SET application_id = 'app_demo_shop', application_type = 'demo_shop'
            WHERE target_id = 'tgt_demo_shop' AND (application_id IS NULL OR application_id = '');
        """)

        # Migration: Ensure demo shop runs are classified as DEMO campaign_type
        cursor.execute("""
            UPDATE test_runs 
            SET campaign_type = 'DEMO', application_id = 'app_demo_shop' 
            WHERE (application_id = 'tgt_demo_shop' OR application_id LIKE '%demo_shop%' OR test_case_id LIKE '%demo_shop%')
              AND campaign_type != 'DEMO';
        """)





