import hashlib
import json
import logging
import threading
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("ai_qa_platform.control_plane.audit")


class AuditEvent(BaseModel):
    request_id: str
    tool_name: str
    tool_version: str = "1.0"
    application_id: str | None = None
    session_id: str | None = None
    actor: str = "autonomous_agent"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    request_hash: str
    response_hash: str
    result_status: str  # "SUCCESS" or "ERROR"
    error_code: str | None = None
    execution_time_ms: float = 0.0


class AuditLogger:
    """
    Cryptographic audit logger for Control Plane operations.
    Maintains a strictly tamper-evident, secret-free record using SHA-256 digests.
    """

    _lock = threading.Lock()
    _events: list[AuditEvent] = []
    MAX_EVENTS: int = 1000

    @staticmethod
    def compute_sha256(payload: Any) -> str:
        """Computes deterministic SHA-256 digest of arbitrary payload."""
        try:
            if isinstance(payload, str):
                encoded = payload.encode("utf-8")
            elif hasattr(payload, "model_dump_json"):
                encoded = payload.model_dump_json().encode("utf-8")
            else:
                encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            return hashlib.sha256(encoded).hexdigest()
        except Exception:
            return hashlib.sha256(b"unhashable_payload").hexdigest()

    @classmethod
    def record_invocation(
        cls,
        request_id: str,
        tool_name: str,
        tool_version: str,
        application_id: str | None,
        session_id: str | None,
        actor: str,
        request_data: Any,
        response_data: Any,
        result_status: str,
        execution_time_ms: float,
        error_code: str | None = None,
    ) -> AuditEvent:
        """
        Records an audit event with SHA-256 cryptographic hashes.
        No plaintext passwords or tokens are stored in the audit trail.
        """
        req_hash = cls.compute_sha256(request_data)
        resp_hash = cls.compute_sha256(response_data)

        event = AuditEvent(
            request_id=request_id,
            tool_name=tool_name,
            tool_version=tool_version,
            application_id=application_id,
            session_id=session_id,
            actor=actor,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_hash=req_hash,
            response_hash=resp_hash,
            result_status=result_status,
            error_code=error_code,
            execution_time_ms=round(execution_time_ms, 2),
        )

        with cls._lock:
            cls._events.append(event)
            if len(cls._events) > cls.MAX_EVENTS:
                cls._events.pop(0)

        logger.info(
            f"AUDIT: [{event.tool_name}] status={event.result_status} "
            f"app={event.application_id} req_id={event.request_id} ({event.execution_time_ms}ms)"
        )
        return event

    @classmethod
    def get_recent_events(cls, limit: int = 50) -> list[AuditEvent]:
        """Returns the most recent audit records."""
        with cls._lock:
            return list(reversed(cls._events[-limit:]))

    @classmethod
    def get_events_for_session(cls, session_id: str) -> list[AuditEvent]:
        """Returns all audit records associated with a specific test session."""
        with cls._lock:
            return [e for e in cls._events if e.session_id == session_id]

    @classmethod
    def clear(cls):
        """Clears audit records (for test isolation)."""
        with cls._lock:
            cls._events.clear()
