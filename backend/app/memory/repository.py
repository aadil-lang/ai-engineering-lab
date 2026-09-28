"""
Slice 8E — Canonical Engineering Memory Repository (SQLite)

Persists structured EngineeringMemory records, candidates, relationships,
and audit logs with versioning and security redaction at rest.
"""

from __future__ import annotations
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from backend.app.memory.models import (
    EngineeringMemory,
    MemoryType,
    MemoryStatus,
    MemoryRelationship,
    RelationshipType,
    MemoryCandidate,
)
from backend.app.control_plane.redaction import RedactionEngine

logger = logging.getLogger("ai_qa_platform.memory_repository")


class EngineeringMemoryRepository:
    """
    Canonical persistent storage for Engineering Memory.
    Invariant: Structured Engineering Memory is the canonical source of learned knowledge.
    """

    def __init__(self, db_path: str = "ai_qa_platform.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS engineering_memories (
                    memory_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    target_id TEXT,
                    component_id TEXT,
                    workflow_id TEXT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_type TEXT,
                    source_run_id TEXT,
                    source_evidence_ids TEXT,
                    source_diagnosis_id TEXT,
                    context_id TEXT,
                    context_hash TEXT,
                    git_commit TEXT,
                    prompt_version INTEGER,
                    model_id TEXT,
                    retrieval_version TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_verified_at TEXT,
                    version INTEGER DEFAULT 1,
                    confidence_metadata TEXT,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_app ON engineering_memories(application_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_type ON engineering_memories(memory_type);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_status ON engineering_memories(status);
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_relationships (
                    relationship_id TEXT PRIMARY KEY,
                    source_memory_id TEXT NOT NULL,
                    target_memory_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    rationale TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_src ON memory_relationships(source_memory_id);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_tgt ON memory_relationships(target_memory_id);
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL,
                    target_id TEXT,
                    component_id TEXT,
                    workflow_id TEXT,
                    proposed_memory_type TEXT NOT NULL,
                    proposed_content TEXT NOT NULL,
                    proposed_status TEXT NOT NULL,
                    source_run_id TEXT NOT NULL,
                    source_evidence_ids TEXT,
                    source_diagnosis_id TEXT,
                    context TEXT,
                    confidence_score REAL DEFAULT 0.7,
                    validation_rules_passed TEXT,
                    status TEXT NOT NULL,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_audit_logs (
                    log_id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_memory(self, memory: EngineeringMemory) -> EngineeringMemory:
        """
        Saves or updates an EngineeringMemory record.
        Applies secret redaction to content before writing to disk.
        """
        from backend.app.control_plane.redaction import RedactionEngine
        sanitized_content, _ = RedactionEngine.redact_text(memory.content)
        memory.content = sanitized_content

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO engineering_memories (
                    memory_id, application_id, target_id, component_id, workflow_id,
                    memory_type, content, status, source_type, source_run_id,
                    source_evidence_ids, source_diagnosis_id, context_id, context_hash,
                    git_commit, prompt_version, model_id, retrieval_version,
                    created_at, updated_at, last_verified_at, version,
                    confidence_metadata, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.memory_id,
                memory.application_id,
                memory.target_id,
                memory.component_id,
                memory.workflow_id,
                memory.memory_type.value,
                memory.content,
                memory.status.value,
                memory.source_type,
                memory.source_run_id,
                json.dumps(memory.source_evidence_ids),
                memory.source_diagnosis_id,
                memory.context_id,
                memory.context_hash,
                memory.git_commit,
                memory.prompt_version,
                memory.model_id,
                memory.retrieval_version,
                memory.created_at,
                memory.updated_at,
                memory.last_verified_at,
                memory.version,
                json.dumps(memory.confidence_metadata),
                json.dumps(memory.tags),
            ))
            conn.commit()
        return memory

    def get_memory(self, memory_id: str) -> Optional[EngineeringMemory]:
        """Fetches memory by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM engineering_memories WHERE memory_id = ?",
                (memory_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_memory(row)

    def list_memories(
        self,
        application_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        status: Optional[MemoryStatus] = None,
        workflow_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EngineeringMemory]:
        """Queries memories matching optional metadata filters."""
        query = "SELECT * FROM engineering_memories WHERE 1=1"
        params: List[Any] = []

        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if workflow_id:
            query += " AND workflow_id = ?"
            params.append(workflow_id)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_memory(r) for r in rows]

    def invalidate_memory(
        self,
        memory_id: str,
        reason: str = "",
        new_status: MemoryStatus = MemoryStatus.INVALIDATED,
    ) -> Optional[EngineeringMemory]:
        """
        Marks memory as INVALIDATED or STALE and records contradiction audit trail.
        Invariant: Contradictions are preserved rather than silently overwritten.
        """
        mem = self.get_memory(memory_id)
        if not mem:
            return None

        mem.status = new_status
        mem.updated_at = datetime.now(timezone.utc).isoformat()
        if reason:
            mem.confidence_metadata["invalidation_reason"] = reason

        self.save_memory(mem)
        self.record_audit_log(memory_id, "MEMORY_INVALIDATED", {"reason": reason, "status": new_status.value})
        return mem

    def supersede_memory(
        self,
        old_memory_id: str,
        new_memory: EngineeringMemory,
        rationale: str = "Superseded by newer evidence",
    ) -> EngineeringMemory:
        """
        Saves new memory and establishes explicit SUPERSEDES relationship.
        Old memory is marked as STALE.
        """
        old_mem = self.get_memory(old_memory_id)
        if old_mem:
            old_mem.status = MemoryStatus.STALE
            old_mem.updated_at = datetime.now(timezone.utc).isoformat()
            self.save_memory(old_mem)

        new_memory.version = (old_mem.version + 1) if old_mem else 1
        saved_new = self.save_memory(new_memory)

        if old_mem:
            rel = MemoryRelationship(
                source_memory_id=saved_new.memory_id,
                target_memory_id=old_memory_id,
                relationship_type=RelationshipType.SUPERSEDES,
                rationale=rationale,
            )
            self.save_relationship(rel)

        self.record_audit_log(
            saved_new.memory_id,
            "MEMORY_SUPERSEDED",
            {"supersedes_memory_id": old_memory_id, "rationale": rationale}
        )
        return saved_new

    def save_relationship(self, rel: MemoryRelationship) -> MemoryRelationship:
        """Persists a relationship edge between memories."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_relationships (
                    relationship_id, source_memory_id, target_memory_id,
                    relationship_type, rationale, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                rel.relationship_id,
                rel.source_memory_id,
                rel.target_memory_id,
                rel.relationship_type.value,
                rel.rationale,
                rel.created_at,
            ))
            conn.commit()
        return rel

    def get_relationships(self, memory_id: str) -> List[MemoryRelationship]:
        """Fetches all inbound and outbound relationships for a memory."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM memory_relationships
                WHERE source_memory_id = ? OR target_memory_id = ?
            """, (memory_id, memory_id)).fetchall()

            return [
                MemoryRelationship(
                    relationship_id=r["relationship_id"],
                    source_memory_id=r["source_memory_id"],
                    target_memory_id=r["target_memory_id"],
                    relationship_type=RelationshipType(r["relationship_type"]),
                    rationale=r["rationale"] or "",
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    def add_relationship(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relationship_type: RelationshipType,
        rationale: Optional[str] = None,
    ) -> MemoryRelationship:
        """Helper to construct and save a MemoryRelationship."""
        rel = MemoryRelationship(
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relationship_type=relationship_type,
            rationale=rationale,
        )
        return self.save_relationship(rel)

    def get_relationships_for_memory(self, memory_id: str) -> List[MemoryRelationship]:
        """Alias for get_relationships."""
        return self.get_relationships(memory_id)

    def save_candidate(self, cand: MemoryCandidate) -> MemoryCandidate:
        """Persists a proposed memory candidate."""
        sanitized_content, _ = RedactionEngine.redact_text(cand.proposed_content)
        cand.proposed_content = sanitized_content

        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_candidates (
                    candidate_id, application_id, target_id, component_id, workflow_id,
                    proposed_memory_type, proposed_content, proposed_status,
                    source_run_id, source_evidence_ids, source_diagnosis_id,
                    context, confidence_score, validation_rules_passed,
                    status, rejection_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cand.candidate_id,
                cand.application_id,
                cand.target_id,
                cand.component_id,
                cand.workflow_id,
                cand.proposed_memory_type.value,
                cand.proposed_content,
                cand.proposed_status.value,
                cand.source_run_id,
                json.dumps(cand.source_evidence_ids),
                cand.source_diagnosis_id,
                json.dumps(cand.context),
                cand.confidence_score,
                json.dumps(cand.validation_rules_passed),
                cand.status,
                cand.rejection_reason,
                cand.created_at,
            ))
            conn.commit()
        return cand

    def get_candidate(self, candidate_id: str) -> Optional[MemoryCandidate]:
        """Fetches candidate by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memory_candidates WHERE candidate_id = ?",
                (candidate_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_candidate(row)

    def list_candidates(
        self,
        application_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[MemoryCandidate]:
        """Lists candidates with optional filters."""
        query = "SELECT * FROM memory_candidates WHERE 1=1"
        params: List[Any] = []
        if application_id:
            query += " AND application_id = ?"
            params.append(application_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_candidate(r) for r in rows]

    def record_audit_log(self, memory_id: str, event_type: str, details: Dict[str, Any]):
        """Records an immutable audit event for memory mutations."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO memory_audit_logs (log_id, memory_id, event_type, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"log_{uuid.uuid4().hex[:8]}",
                memory_id,
                event_type,
                json.dumps(details),
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()

    def compact_memories(self, application_id: str, max_memories: int = 500) -> int:
        """
        Bounds memory accumulation by pruning or archiving old stale/invalidated memories.
        Evidence is never deleted.
        """
        with self._get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM engineering_memories WHERE application_id = ?",
                (application_id,)
            ).fetchone()[0]

            if count <= max_memories:
                return 0

            excess = count - max_memories
            # Remove oldest INVALIDATED or STALE memories first
            cursor = conn.execute("""
                DELETE FROM engineering_memories
                WHERE memory_id IN (
                    SELECT memory_id FROM engineering_memories
                    WHERE application_id = ? AND status IN ('INVALIDATED', 'STALE')
                    ORDER BY updated_at ASC
                    LIMIT ?
                )
            """, (application_id, excess))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def _row_to_memory(self, row: sqlite3.Row) -> EngineeringMemory:
        return EngineeringMemory(
            memory_id=row["memory_id"],
            application_id=row["application_id"],
            target_id=row["target_id"],
            component_id=row["component_id"],
            workflow_id=row["workflow_id"],
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            status=MemoryStatus(row["status"]),
            source_type=row["source_type"] or "RUN_EXECUTION",
            source_run_id=row["source_run_id"],
            source_evidence_ids=json.loads(row["source_evidence_ids"] or "[]"),
            source_diagnosis_id=row["source_diagnosis_id"],
            context_id=row["context_id"],
            context_hash=row["context_hash"],
            git_commit=row["git_commit"],
            prompt_version=row["prompt_version"],
            model_id=row["model_id"],
            retrieval_version=row["retrieval_version"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_verified_at=row["last_verified_at"],
            version=row["version"],
            confidence_metadata=json.loads(row["confidence_metadata"] or "{}"),
            tags=json.loads(row["tags"] or "[]"),
        )

    def _row_to_candidate(self, row: sqlite3.Row) -> MemoryCandidate:
        return MemoryCandidate(
            candidate_id=row["candidate_id"],
            application_id=row["application_id"],
            target_id=row["target_id"],
            component_id=row["component_id"],
            workflow_id=row["workflow_id"],
            proposed_memory_type=MemoryType(row["proposed_memory_type"]),
            proposed_content=row["proposed_content"],
            proposed_status=MemoryStatus(row["proposed_status"]),
            source_run_id=row["source_run_id"],
            source_evidence_ids=json.loads(row["source_evidence_ids"] or "[]"),
            source_diagnosis_id=row["source_diagnosis_id"],
            context=json.loads(row["context"] or "{}"),
            confidence_score=row["confidence_score"],
            validation_rules_passed=json.loads(row["validation_rules_passed"] or "[]"),
            status=row["status"],
            rejection_reason=row["rejection_reason"],
            created_at=row["created_at"],
        )
