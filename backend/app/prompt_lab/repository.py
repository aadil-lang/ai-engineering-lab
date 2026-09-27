import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.prompt_lab.models import (
    PromptDefinition,
    PromptVersion,
    PromptStatus,
    EvaluationSuite,
    EvaluationSuiteVersion,
    EvaluationCase,
    EvaluationRun,
    CaseEvaluationResult,
    PromptDiagnosis,
    PromptImprovementCandidate,
    EvaluationSnapshot,
)
from backend.app.prompt_lab.errors import (
    PromptNotFoundError,
    PromptVersionNotFoundError,
    PromptVersionImmutableError,
    EvaluationSuiteNotFoundError,
    EvaluationSnapshotTamperedError,
    CandidateNotFoundError,
)


class PromptLabRepository:
    """
    Persistence store for Prompt Reliability Lab:
    - Immutable prompt definitions and prompt versions
    - Versioned evaluation suites and frozen cases
    - Execution runs and per-case evaluation results
    - Evidence-backed diagnoses and improvement candidates
    - Cryptographically verified evaluation snapshots
    """

    def __init__(self, db_path: str = "backend/data/reliability_platform.db"):
        self.db_path = db_path
        self._prompts: Dict[str, PromptDefinition] = {}
        self._prompt_versions: Dict[str, Dict[int, PromptVersion]] = {}
        self._suites: Dict[str, EvaluationSuite] = {}
        self._suite_versions: Dict[str, Dict[int, EvaluationSuiteVersion]] = {}
        self._runs: Dict[str, EvaluationRun] = {}
        self._diagnoses: Dict[str, PromptDiagnosis] = {}
        self._candidates: Dict[str, PromptImprovementCandidate] = {}
        self._snapshots: Dict[str, EvaluationSnapshot] = {}

        self._conn = sqlite3.connect(":memory:", check_same_thread=False) if db_path == ":memory:" else None
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        """Ensures SQLite tables exist for Prompt Lab persistence."""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_definitions (
                prompt_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_versions (
                prompt_id TEXT,
                version INTEGER,
                template TEXT NOT NULL,
                variables_schema TEXT,
                output_schema TEXT,
                components TEXT,
                parent_version INTEGER,
                change_reason TEXT,
                status TEXT,
                is_evaluated INTEGER,
                created_at TEXT,
                PRIMARY KEY (prompt_id, version)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_suites (
                suite_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_suite_versions (
                suite_id TEXT,
                version INTEGER,
                description TEXT,
                cases_json TEXT,
                is_frozen INTEGER,
                created_at TEXT,
                PRIMARY KEY (suite_id, version)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_evaluation_runs (
                evaluation_run_id TEXT PRIMARY KEY,
                prompt_id TEXT,
                prompt_version INTEGER,
                suite_id TEXT,
                suite_version INTEGER,
                model TEXT,
                generation_parameters TEXT,
                status TEXT,
                total_cases INTEGER,
                passed_cases INTEGER,
                failed_cases INTEGER,
                partial_cases INTEGER,
                unknown_cases INTEGER,
                abstained_cases INTEGER,
                pass_rate REAL,
                case_results_json TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_ms INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_diagnoses (
                diagnosis_id TEXT PRIMARY KEY,
                evaluation_run_id TEXT,
                case_id TEXT,
                primary_cause TEXT,
                confidence REAL,
                facts_json TEXT,
                observed_summary TEXT,
                inferred_summary TEXT,
                hypothesis_summary TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_candidates (
                candidate_id TEXT PRIMARY KEY,
                source_prompt_version INTEGER,
                proposed_template TEXT,
                proposed_components TEXT,
                rationale TEXT,
                evidence_ids TEXT,
                diagnosis_ids TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                prompt_id TEXT,
                prompt_version INTEGER,
                suite_id TEXT,
                suite_version INTEGER,
                model TEXT,
                content_json TEXT,
                sha256_hash TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()

    # 1. Prompt Definition & Version Methods
    def save_prompt(self, prompt: PromptDefinition) -> PromptDefinition:
        self._prompts[prompt.prompt_id] = prompt
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_definitions (prompt_id, name, description, created_at)
            VALUES (?, ?, ?, ?)
        """, (prompt.prompt_id, prompt.name, prompt.description, prompt.created_at))
        conn.commit()
        return prompt

    def get_prompt(self, prompt_id: str) -> Optional[PromptDefinition]:
        if prompt_id in self._prompts:
            return self._prompts[prompt_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT prompt_id, name, description, created_at FROM prompt_definitions WHERE prompt_id = ?", (prompt_id,))
        row = cursor.fetchone()
        if not row:
            return None
        p = PromptDefinition(prompt_id=row[0], name=row[1], description=row[2], created_at=row[3])
        self._prompts[prompt_id] = p
        return p

    def list_prompts(self) -> List[PromptDefinition]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT prompt_id, name, description, created_at FROM prompt_definitions ORDER BY created_at DESC")
        prompts = []
        for row in cursor.fetchall():
            p = PromptDefinition(prompt_id=row[0], name=row[1], description=row[2], created_at=row[3])
            prompts.append(p)
            self._prompts[p.prompt_id] = p
        return prompts

    def save_prompt_version(self, pv: PromptVersion) -> PromptVersion:
        # Check immutability if existing
        existing = self.get_prompt_version(pv.prompt_id, pv.version)
        if existing and existing.is_evaluated:
            if (
                existing.template != pv.template
                or existing.variables_schema != pv.variables_schema
                or existing.output_schema != pv.output_schema
                or existing.components != pv.components
            ):
                raise PromptVersionImmutableError(
                    f"Prompt version {pv.prompt_id}:v{pv.version} has already been evaluated and is immutable."
                )

        if pv.prompt_id not in self._prompt_versions:
            self._prompt_versions[pv.prompt_id] = {}
        self._prompt_versions[pv.prompt_id][pv.version] = pv

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_versions (
                prompt_id, version, template, variables_schema, output_schema,
                components, parent_version, change_reason, status, is_evaluated, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pv.prompt_id,
            pv.version,
            pv.template,
            json.dumps(pv.variables_schema),
            json.dumps(pv.output_schema) if pv.output_schema else None,
            json.dumps(pv.components.model_dump()) if pv.components else None,
            pv.parent_version,
            pv.change_reason,
            pv.status.value,
            1 if pv.is_evaluated else 0,
            pv.created_at,
        ))
        conn.commit()
        return pv

    def mark_prompt_version_evaluated(self, prompt_id: str, version: int):
        pv = self.get_prompt_version(prompt_id, version)
        if not pv:
            raise PromptVersionNotFoundError(f"Prompt version {prompt_id}:v{version} not found.")
        pv.is_evaluated = True
        if pv.status == PromptStatus.DRAFT:
            pv.status = PromptStatus.EVALUATING
        self.save_prompt_version(pv)

    def get_prompt_version(self, prompt_id: str, version: int) -> Optional[PromptVersion]:
        if prompt_id in self._prompt_versions and version in self._prompt_versions[prompt_id]:
            return self._prompt_versions[prompt_id][version]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT prompt_id, version, template, variables_schema, output_schema,
                   components, parent_version, change_reason, status, is_evaluated, created_at
            FROM prompt_versions WHERE prompt_id = ? AND version = ?
        """, (prompt_id, version))
        row = cursor.fetchone()
        if not row:
            return None
        pv = PromptVersion(
            prompt_id=row[0],
            version=row[1],
            template=row[2],
            variables_schema=json.loads(row[3]) if row[3] else {},
            output_schema=json.loads(row[4]) if row[4] else None,
            components=json.loads(row[5]) if row[5] else None,
            parent_version=row[6],
            change_reason=row[7],
            status=PromptStatus(row[8]),
            is_evaluated=bool(row[9]),
            created_at=row[10],
        )
        if prompt_id not in self._prompt_versions:
            self._prompt_versions[prompt_id] = {}
        self._prompt_versions[prompt_id][version] = pv
        return pv

    def list_prompt_versions(self, prompt_id: str) -> List[PromptVersion]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT prompt_id, version, template, variables_schema, output_schema,
                   components, parent_version, change_reason, status, is_evaluated, created_at
            FROM prompt_versions WHERE prompt_id = ? ORDER BY version ASC
        """, (prompt_id,))
        results = []
        for row in cursor.fetchall():
            pv = PromptVersion(
                prompt_id=row[0],
                version=row[1],
                template=row[2],
                variables_schema=json.loads(row[3]) if row[3] else {},
                output_schema=json.loads(row[4]) if row[4] else None,
                components=json.loads(row[5]) if row[5] else None,
                parent_version=row[6],
                change_reason=row[7],
                status=PromptStatus(row[8]),
                is_evaluated=bool(row[9]),
                created_at=row[10],
            )
            results.append(pv)
            if prompt_id not in self._prompt_versions:
                self._prompt_versions[prompt_id] = {}
            self._prompt_versions[prompt_id][pv.version] = pv
        return results

    # 2. Evaluation Suite Methods
    def save_suite(self, suite: EvaluationSuite) -> EvaluationSuite:
        self._suites[suite.suite_id] = suite
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO evaluation_suites (suite_id, name, description, created_at)
            VALUES (?, ?, ?, ?)
        """, (suite.suite_id, suite.name, suite.description, suite.created_at))
        conn.commit()
        return suite

    def get_suite(self, suite_id: str) -> Optional[EvaluationSuite]:
        if suite_id in self._suites:
            return self._suites[suite_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT suite_id, name, description, created_at FROM evaluation_suites WHERE suite_id = ?", (suite_id,))
        row = cursor.fetchone()
        if not row:
            return None
        s = EvaluationSuite(suite_id=row[0], name=row[1], description=row[2], created_at=row[3])
        self._suites[suite_id] = s
        return s

    def list_suites(self) -> List[EvaluationSuite]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT suite_id, name, description, created_at FROM evaluation_suites ORDER BY created_at DESC")
        results = []
        for row in cursor.fetchall():
            s = EvaluationSuite(suite_id=row[0], name=row[1], description=row[2], created_at=row[3])
            results.append(s)
            self._suites[s.suite_id] = s
        return results

    def save_suite_version(self, sv: EvaluationSuiteVersion) -> EvaluationSuiteVersion:
        existing = self.get_suite_version(sv.suite_id, sv.version)
        if existing and existing.is_frozen:
            existing_cases_dump = [c.model_dump() for c in existing.cases]
            new_cases_dump = [c.model_dump() for c in sv.cases]
            if existing_cases_dump != new_cases_dump or existing.description != sv.description:
                raise PromptVersionImmutableError(
                    f"Evaluation suite version {sv.suite_id}:v{sv.version} is frozen and immutable."
                )

        if sv.suite_id not in self._suite_versions:
            self._suite_versions[sv.suite_id] = {}
        self._suite_versions[sv.suite_id][sv.version] = sv

        cases_json = json.dumps([c.model_dump() for c in sv.cases])
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO evaluation_suite_versions (
                suite_id, version, description, cases_json, is_frozen, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (sv.suite_id, sv.version, sv.description, cases_json, 1 if sv.is_frozen else 0, sv.created_at))
        conn.commit()
        return sv

    def freeze_suite_version(self, suite_id: str, version: int):
        sv = self.get_suite_version(suite_id, version)
        if not sv:
            raise EvaluationSuiteNotFoundError(f"Suite version {suite_id}:v{version} not found.")
        sv.is_frozen = True
        self.save_suite_version(sv)

    def get_suite_version(self, suite_id: str, version: int) -> Optional[EvaluationSuiteVersion]:
        if suite_id in self._suite_versions and version in self._suite_versions[suite_id]:
            return self._suite_versions[suite_id][version]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT suite_id, version, description, cases_json, is_frozen, created_at
            FROM evaluation_suite_versions WHERE suite_id = ? AND version = ?
        """, (suite_id, version))
        row = cursor.fetchone()
        if not row:
            return None
        cases_raw = json.loads(row[3]) if row[3] else []
        cases = [EvaluationCase(**c) for c in cases_raw]
        sv = EvaluationSuiteVersion(
            suite_id=row[0],
            version=row[1],
            description=row[2],
            cases=cases,
            is_frozen=bool(row[4]),
            created_at=row[5],
        )
        if suite_id not in self._suite_versions:
            self._suite_versions[suite_id] = {}
        self._suite_versions[suite_id][version] = sv
        return sv

    # 3. Evaluation Run Methods
    def save_run(self, run: EvaluationRun) -> EvaluationRun:
        self._runs[run.evaluation_run_id] = run
        case_results_json = json.dumps([cr.model_dump() for cr in run.case_results])
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_evaluation_runs (
                evaluation_run_id, prompt_id, prompt_version, suite_id, suite_version,
                model, generation_parameters, status, total_cases, passed_cases,
                failed_cases, partial_cases, unknown_cases, abstained_cases, pass_rate,
                case_results_json, started_at, completed_at, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.evaluation_run_id,
            run.prompt_id,
            run.prompt_version,
            run.suite_id,
            run.suite_version,
            run.model,
            json.dumps(run.generation_parameters),
            run.status,
            run.total_cases,
            run.passed_cases,
            run.failed_cases,
            run.partial_cases,
            run.unknown_cases,
            run.abstained_cases,
            run.pass_rate,
            case_results_json,
            run.started_at,
            run.completed_at,
            run.duration_ms,
        ))
        conn.commit()
        return run

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        if run_id in self._runs:
            return self._runs[run_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT evaluation_run_id, prompt_id, prompt_version, suite_id, suite_version,
                   model, generation_parameters, status, total_cases, passed_cases,
                   failed_cases, partial_cases, unknown_cases, abstained_cases, pass_rate,
                   case_results_json, started_at, completed_at, duration_ms
            FROM prompt_evaluation_runs WHERE evaluation_run_id = ?
        """, (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cases_raw = json.loads(row[15]) if row[15] else []
        case_results = [CaseEvaluationResult(**cr) for cr in cases_raw]
        run = EvaluationRun(
            evaluation_run_id=row[0],
            prompt_id=row[1],
            prompt_version=row[2],
            suite_id=row[3],
            suite_version=row[4],
            model=row[5],
            generation_parameters=json.loads(row[6]) if row[6] else {},
            status=row[7],
            total_cases=row[8],
            passed_cases=row[9],
            failed_cases=row[10],
            partial_cases=row[11],
            unknown_cases=row[12],
            abstained_cases=row[13],
            pass_rate=row[14],
            case_results=case_results,
            started_at=row[16],
            completed_at=row[17],
            duration_ms=row[18],
        )
        self._runs[run_id] = run
        return run

    def list_runs_for_prompt(self, prompt_id: str, version: Optional[int] = None) -> List[EvaluationRun]:
        conn = self._get_conn()
        cursor = conn.cursor()
        if version is not None:
            cursor.execute("""
                SELECT evaluation_run_id FROM prompt_evaluation_runs
                WHERE prompt_id = ? AND prompt_version = ? ORDER BY started_at DESC
            """, (prompt_id, version))
        else:
            cursor.execute("""
                SELECT evaluation_run_id FROM prompt_evaluation_runs
                WHERE prompt_id = ? ORDER BY started_at DESC
            """, (prompt_id,))
        results = []
        for (run_id,) in cursor.fetchall():
            run = self.get_run(run_id)
            if run:
                results.append(run)
        return results

    # 4. Diagnoses & Candidates
    def save_diagnosis(self, diag: PromptDiagnosis) -> PromptDiagnosis:
        self._diagnoses[diag.diagnosis_id] = diag
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_diagnoses (
                diagnosis_id, evaluation_run_id, case_id, primary_cause, confidence,
                facts_json, observed_summary, inferred_summary, hypothesis_summary, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            diag.diagnosis_id,
            diag.evaluation_run_id,
            diag.case_id,
            diag.primary_cause.value,
            diag.confidence,
            json.dumps([f.model_dump() for f in diag.facts]),
            diag.observed_summary,
            diag.inferred_summary,
            diag.hypothesis_summary,
            diag.created_at,
        ))
        conn.commit()
        return diag

    def get_diagnosis(self, diagnosis_id: str) -> Optional[PromptDiagnosis]:
        if diagnosis_id in self._diagnoses:
            return self._diagnoses[diagnosis_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT diagnosis_id, evaluation_run_id, case_id, primary_cause, confidence,
                   facts_json, observed_summary, inferred_summary, hypothesis_summary, created_at
            FROM prompt_diagnoses WHERE diagnosis_id = ?
        """, (diagnosis_id,))
        row = cursor.fetchone()
        if not row:
            return None
        from backend.app.prompt_lab.models import DiagnosticFact, FailureCause
        facts_raw = json.loads(row[5]) if row[5] else []
        facts = [DiagnosticFact(**f) for f in facts_raw]
        diag = PromptDiagnosis(
            diagnosis_id=row[0],
            evaluation_run_id=row[1],
            case_id=row[2],
            primary_cause=FailureCause(row[3]),
            confidence=row[4],
            facts=facts,
            observed_summary=row[6],
            inferred_summary=row[7],
            hypothesis_summary=row[8],
            created_at=row[9],
        )
        self._diagnoses[diagnosis_id] = diag
        return diag

    def list_diagnoses_for_run(self, evaluation_run_id: str) -> List[PromptDiagnosis]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT diagnosis_id FROM prompt_diagnoses WHERE evaluation_run_id = ?", (evaluation_run_id,))
        diags = []
        for (diag_id,) in cursor.fetchall():
            d = self.get_diagnosis(diag_id)
            if d:
                diags.append(d)
        return diags

    def save_candidate(self, cand: PromptImprovementCandidate) -> PromptImprovementCandidate:
        self._candidates[cand.candidate_id] = cand
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_candidates (
                candidate_id, source_prompt_version, proposed_template, proposed_components,
                rationale, evidence_ids, diagnosis_ids, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cand.candidate_id,
            cand.source_prompt_version,
            cand.proposed_template,
            json.dumps(cand.proposed_components.model_dump()) if cand.proposed_components else None,
            cand.rationale,
            json.dumps(cand.evidence_ids),
            json.dumps(cand.diagnosis_ids),
            cand.status.value,
            cand.created_at,
        ))
        conn.commit()
        return cand

    def get_candidate(self, candidate_id: str) -> Optional[PromptImprovementCandidate]:
        if candidate_id in self._candidates:
            return self._candidates[candidate_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT candidate_id, source_prompt_version, proposed_template, proposed_components,
                   rationale, evidence_ids, diagnosis_ids, status, created_at
            FROM prompt_candidates WHERE candidate_id = ?
        """, (candidate_id,))
        row = cursor.fetchone()
        if not row:
            return None
        from backend.app.prompt_lab.models import CandidateStatus, StructuredPromptComponents
        cand = PromptImprovementCandidate(
            candidate_id=row[0],
            source_prompt_version=row[1],
            proposed_template=row[2],
            proposed_components=StructuredPromptComponents(**json.loads(row[3])) if row[3] else None,
            rationale=row[4],
            evidence_ids=json.loads(row[5]) if row[5] else [],
            diagnosis_ids=json.loads(row[6]) if row[6] else [],
            status=CandidateStatus(row[7]),
            created_at=row[8],
        )
        self._candidates[candidate_id] = cand
        return cand

    # 5. Immutable Evaluation Snapshot
    def save_snapshot(self, snap: EvaluationSnapshot) -> EvaluationSnapshot:
        # Verify hash integrity
        content_dict = {
            "snapshot_id": snap.snapshot_id,
            "protocol_version": snap.protocol_version,
            "prompt_id": snap.prompt_id,
            "prompt_version": snap.prompt_version,
            "suite_id": snap.suite_id,
            "suite_version": snap.suite_version,
            "model": snap.model,
            "model_parameters": snap.model_parameters,
            "dataset_provenance": snap.dataset_provenance,
            "evaluation_run_id": snap.evaluation_run_id,
            "total_cases": snap.total_cases,
            "passed_cases": snap.passed_cases,
            "failed_cases": snap.failed_cases,
            "pass_rate": snap.pass_rate,
            "evaluator_versions": snap.evaluator_versions,
            "timestamp": snap.timestamp,
        }
        computed_hash = hashlib.sha256(json.dumps(content_dict, sort_keys=True).encode("utf-8")).hexdigest()
        if snap.sha256_hash != computed_hash:
            raise EvaluationSnapshotTamperedError(
                f"Evaluation snapshot hash mismatch: declared {snap.sha256_hash} vs computed {computed_hash}"
            )

        self._snapshots[snap.snapshot_id] = snap
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO prompt_snapshots (
                snapshot_id, prompt_id, prompt_version, suite_id, suite_version,
                model, content_json, sha256_hash, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snap.snapshot_id,
            snap.prompt_id,
            snap.prompt_version,
            snap.suite_id,
            snap.suite_version,
            snap.model,
            json.dumps(content_dict),
            snap.sha256_hash,
            snap.timestamp,
        ))
        conn.commit()
        return snap

    def get_snapshot(self, snapshot_id: str) -> Optional[EvaluationSnapshot]:
        if snapshot_id in self._snapshots:
            return self._snapshots[snapshot_id]
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT snapshot_id, prompt_id, prompt_version, suite_id, suite_version,
                   model, content_json, sha256_hash, timestamp
            FROM prompt_snapshots WHERE snapshot_id = ?
        """, (snapshot_id,))
        row = cursor.fetchone()
        if not row:
            return None
        content = json.loads(row[6])
        stored_hash = row[7]
        computed_hash = hashlib.sha256(json.dumps(content, sort_keys=True).encode("utf-8")).hexdigest()
        if stored_hash != computed_hash:
            raise EvaluationSnapshotTamperedError(f"Snapshot {snapshot_id} has been tampered with.")
        snap = EvaluationSnapshot(
            snapshot_id=row[0],
            prompt_id=row[1],
            prompt_version=row[2],
            suite_id=row[3],
            suite_version=row[4],
            model=row[5],
            model_parameters=content.get("model_parameters", {}),
            dataset_provenance=content.get("dataset_provenance", {}),
            evaluation_run_id=content.get("evaluation_run_id", ""),
            total_cases=content.get("total_cases", 0),
            passed_cases=content.get("passed_cases", 0),
            failed_cases=content.get("failed_cases", 0),
            pass_rate=content.get("pass_rate", 0.0),
            evaluator_versions=content.get("evaluator_versions", {}),
            sha256_hash=stored_hash,
            timestamp=row[8],
        )
        self._snapshots[snapshot_id] = snap
        return snap
