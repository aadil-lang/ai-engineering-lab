from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from backend.app.models.failure import Failure
from backend.app.models.evidence import Evidence
from backend.app.models.test_action import TestAction

class DiagnosticReport(BaseModel):
    report_id: str
    run_id: str
    root_cause_summary: str
    probable_subsystem: str # Frontend, Backend API, Database, Network, LLM Integration
    confidence_score: float # 0.0 to 1.0
    contributing_factors: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    remediation_recommendations: list[str] = Field(default_factory=list)

class BaseDiagnostician(ABC):
    """
    Contract for Diagnostic Engine in Engineering Feedback Loop.
    Detect -> Evidence -> Diagnose -> Engineering Feedback -> Coding-Agent Fix Package -> Retest -> Verify.
    """
    @abstractmethod
    async def diagnose_failure(
        self,
        failures: list[Failure],
        actions: list[TestAction],
        evidence_bundle: list[Evidence],
    ) -> DiagnosticReport:
        pass
