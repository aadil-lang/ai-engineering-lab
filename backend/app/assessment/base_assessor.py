from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from backend.app.models.assessment import Assessment, AssessmentFinding, DimensionScore
from backend.app.models.enums import AssessmentDimension

class AssessmentConfig(BaseModel):
    application_id: str
    target_url: str
    dimensions_to_evaluate: list[AssessmentDimension] = Field(
        default_factory=lambda: list(AssessmentDimension)
    )
    load_test_vus: int = 10
    load_test_duration_sec: int = 30
    security_scan_depth: str = "baseline" # baseline | active_fuzzing
    chaos_fault_type: str | None = None # latency_injection | service_kill

class BaseDimensionAssessor(ABC):
    """Abstract evaluator for a specific production readiness dimension."""
    @property
    @abstractmethod
    def dimension(self) -> AssessmentDimension:
        pass

    @abstractmethod
    async def evaluate(self, config: AssessmentConfig) -> tuple[DimensionScore, list[AssessmentFinding]]:
        """Run evaluation tools and return dimension score + findings."""
        pass

class K6LoadAdapter(ABC):
    """Adapter interface for k6 load/capacity testing."""
    @abstractmethod
    async def run_scenario(self, target_url: str, vus: int, duration_sec: int) -> dict:
        pass

class OTelTraceAdapter(ABC):
    """Adapter interface for OpenTelemetry trace & span evaluation."""
    @abstractmethod
    async def fetch_traces(self, service_name: str, lookback_sec: int) -> list[dict]:
        pass

class PrometheusMetricsAdapter(ABC):
    """Adapter interface for Prometheus metric queries."""
    @abstractmethod
    async def query_metric(self, query: str) -> dict:
        pass

class OwaspZapSecurityAdapter(ABC):
    """Adapter interface for OWASP ZAP baseline / active scan."""
    @abstractmethod
    async def scan_target(self, target_url: str) -> list[dict]:
        pass

class ChaosMeshAdapter(ABC):
    """Adapter interface for Chaos engineering & failure recovery testing."""
    @abstractmethod
    async def inject_fault(self, fault_config: dict) -> dict:
        pass
