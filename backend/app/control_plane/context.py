from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class ToolInvocationContext(BaseModel):
    """
    Invocation context accompanying every agent tool call across the control plane.
    """
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    actor: str = "autonomous_agent"
    session_id: str | None = None
    idempotency_key: str | None = None
    auth_token: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create_default(
        cls,
        session_id: str | None = None,
        idempotency_key: str | None = None,
        actor: str = "autonomous_agent",
    ) -> "ToolInvocationContext":
        return cls(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            actor=actor,
            session_id=session_id,
            idempotency_key=idempotency_key,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
