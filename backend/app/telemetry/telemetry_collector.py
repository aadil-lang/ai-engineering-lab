from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from backend.app.models.metric import Metric

class TelemetrySpan(BaseModel):
    span_id: str
    trace_id: str
    name: str
    duration_ms: float
    status: str
    attributes: dict = Field(default_factory=dict)
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class TelemetryLogEvent(BaseModel):
    event_id: str
    run_id: str
    level: str # INFO, WARN, ERROR, DEBUG
    message: str
    context: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BaseTelemetryCollector(ABC):
    """Contract for ingesting metrics, spans, and event streams."""
    @abstractmethod
    async def record_metric(self, metric: Metric) -> None:
        pass

    @abstractmethod
    async def record_span(self, span: TelemetrySpan) -> None:
        pass

    @abstractmethod
    async def record_log(self, log_event: TelemetryLogEvent) -> None:
        pass
