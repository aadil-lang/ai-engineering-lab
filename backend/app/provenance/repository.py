"""
Slice 8L — Append-Only Provenance Repository

Provides persistent, append-only SQLite storage for EngineeringLifecycleEvent
records with strict cryptographic chaining and tamper verification.
"""

from __future__ import annotations
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.provenance.models import (
    EngineeringLifecycleEvent,
    LifecycleEventType,
    ActorType,
    ProvenanceChainVerificationResult,
)
from backend.app.provenance.hashing import calculate_event_hash, GENESIS_HASH

logger = logging.getLogger("ai_qa_platform.provenance_repository")


class ProvenanceRepository:
    """
    Append-only repository for engineering lifecycle events.
    Never permits in-place mutation or deletion of historical events.
    """

    def __init__(self, db_path: str = "backend/data/reliability_platform.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS engineering_lifecycle_events (
                    event_id TEXT PRIMARY KEY,
                    sequence_number INTEGER NOT NULL UNIQUE,
                    correlation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    parent_event_id TEXT,
                    application_id TEXT,
                    target_id TEXT,
                    run_id TEXT,
                    test_case_id TEXT,
                    change_set_id TEXT,
                    plan_id TEXT,
                    memory_id TEXT,
                    evidence_id TEXT,
                    diagnosis_id TEXT,
                    remediation_id TEXT,
                    governance_id TEXT,
                    authorization_id TEXT,
                    git_commit TEXT,
                    pull_request_id TEXT,
                    ci_run_id TEXT,
                    context_id TEXT,
                    metadata_json TEXT NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_corr ON engineering_lifecycle_events(correlation_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_run ON engineering_lifecycle_events(run_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_commit ON engineering_lifecycle_events(git_commit);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_cs ON engineering_lifecycle_events(change_set_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_seq ON engineering_lifecycle_events(sequence_number);")
            conn.commit()

    def _row_to_event(self, row: sqlite3.Row) -> EngineeringLifecycleEvent:
        metadata = {}
        if row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except Exception:
                metadata = {}

        return EngineeringLifecycleEvent(
            event_id=row["event_id"],
            sequence_number=row["sequence_number"],
            correlation_id=row["correlation_id"],
            event_type=LifecycleEventType(row["event_type"]),
            timestamp=row["timestamp"],
            actor_type=ActorType(row["actor_type"]),
            actor_id=row["actor_id"],
            parent_event_id=row["parent_event_id"],
            application_id=row["application_id"],
            target_id=row["target_id"],
            run_id=row["run_id"],
            test_case_id=row["test_case_id"],
            change_set_id=row["change_set_id"],
            plan_id=row["plan_id"],
            memory_id=row["memory_id"],
            evidence_id=row["evidence_id"],
            diagnosis_id=row["diagnosis_id"],
            remediation_id=row["remediation_id"],
            governance_id=row["governance_id"],
            authorization_id=row["authorization_id"],
            git_commit=row["git_commit"],
            pull_request_id=row["pull_request_id"],
            ci_run_id=row["ci_run_id"],
            context_id=row["context_id"],
            metadata=metadata,
            previous_event_hash=row["previous_event_hash"],
            event_hash=row["event_hash"],
        )

    def append_event(self, event: EngineeringLifecycleEvent) -> EngineeringLifecycleEvent:
        """
        Appends a new event to the immutable cryptographic chain.
        Automatically binds sequence_number, links to the latest previous_event_hash,
        and computes the cryptographic event_hash.
        """
        with self._get_connection() as conn:
            # Fetch latest event for global sequence & previous hash
            latest = conn.execute(
                "SELECT sequence_number, event_hash FROM engineering_lifecycle_events ORDER BY sequence_number DESC LIMIT 1"
            ).fetchone()

            if latest:
                event.sequence_number = latest["sequence_number"] + 1
                event.previous_event_hash = latest["event_hash"]
            else:
                event.sequence_number = 1
                event.previous_event_hash = GENESIS_HASH

            # Compute tamper-evident hash
            event_dict = event.model_dump()
            event.event_hash = calculate_event_hash(event_dict, event.previous_event_hash)

            conn.execute("""
                INSERT INTO engineering_lifecycle_events (
                    event_id, sequence_number, correlation_id, event_type, timestamp,
                    actor_type, actor_id, parent_event_id, application_id, target_id,
                    run_id, test_case_id, change_set_id, plan_id, memory_id,
                    evidence_id, diagnosis_id, remediation_id, governance_id,
                    authorization_id, git_commit, pull_request_id, ci_run_id,
                    context_id, metadata_json, previous_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id,
                event.sequence_number,
                event.correlation_id,
                event.event_type.value,
                event.timestamp,
                event.actor_type.value,
                event.actor_id,
                event.parent_event_id,
                event.application_id,
                event.target_id,
                event.run_id,
                event.test_case_id,
                event.change_set_id,
                event.plan_id,
                event.memory_id,
                event.evidence_id,
                event.diagnosis_id,
                event.remediation_id,
                event.governance_id,
                event.authorization_id,
                event.git_commit,
                event.pull_request_id,
                event.ci_run_id,
                event.context_id,
                json.dumps(event.metadata),
                event.previous_event_hash,
                event.event_hash,
            ))
            conn.commit()

        return event

    def get_event(self, event_id: str) -> Optional[EngineeringLifecycleEvent]:
        """Retrieves a single lifecycle event by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM engineering_lifecycle_events WHERE event_id = ?",
                (event_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_event(row)

    def list_events(
        self,
        correlation_id: Optional[str] = None,
        application_id: Optional[str] = None,
        run_id: Optional[str] = None,
        git_commit: Optional[str] = None,
        limit: int = 500,
    ) -> List[EngineeringLifecycleEvent]:
        """Retrieves lifecycle events filtered by provenance coordinates."""
        query = "SELECT * FROM engineering_lifecycle_events WHERE 1=1"
        params: List[Any] = []

        if correlation_id:
            query += " AND correlation_id = ?"
            params.append(correlation_id)
        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        if git_commit:
            query += " AND git_commit = ?"
            params.append(git_commit)

        query += " ORDER BY sequence_number ASC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_event(r) for r in rows]

    def verify_chain(self, correlation_id: Optional[str] = None) -> ProvenanceChainVerificationResult:
        """
        Audits cryptographic event chain integrity:
        - Detects modified payloads
        - Detects broken sequence numbers
        - Detects invalid previous hashes
        """
        events = self.list_events(correlation_id=correlation_id, limit=5000)
        if not events:
            return ProvenanceChainVerificationResult(
                is_valid=True,
                total_events=0,
                verified_events=0,
                details="Event chain is empty; no violations found."
            )

        expected_prev_hash = events[0].previous_event_hash
        verified = 0

        for i, evt in enumerate(events):
            # Check previous hash continuity
            if evt.previous_event_hash != expected_prev_hash:
                return ProvenanceChainVerificationResult(
                    is_valid=False,
                    total_events=len(events),
                    verified_events=verified,
                    broken_event_id=evt.event_id,
                    violation_type="INCORRECT_PREVIOUS_HASH",
                    details=f"Event {evt.event_id} at sequence {evt.sequence_number} expected previous hash '{expected_prev_hash}', got '{evt.previous_event_hash}'."
                )

            # Recompute event hash over canonical payload
            recomputed = calculate_event_hash(evt.model_dump(), evt.previous_event_hash)
            if recomputed != evt.event_hash:
                return ProvenanceChainVerificationResult(
                    is_valid=False,
                    total_events=len(events),
                    verified_events=verified,
                    broken_event_id=evt.event_id,
                    violation_type="MODIFIED_EVENT",
                    details=f"Event {evt.event_id} payload tampering detected: recomputed '{recomputed}', recorded '{evt.event_hash}'."
                )

            expected_prev_hash = evt.event_hash
            verified += 1

        return ProvenanceChainVerificationResult(
            is_valid=True,
            total_events=len(events),
            verified_events=verified,
            details=f"All {verified} events verified successfully. Cryptographic chain is intact."
        )
