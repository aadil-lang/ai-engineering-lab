from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from backend.app.diagnosis.base_diagnostician import DiagnosticReport

class RemediationPatchSpec(BaseModel):
    file_path: str
    target_symbol: str | None = None
    description_of_change: str
    suggested_diff: str | None = None

class EngineeringFixPackage(BaseModel):
    package_id: str
    run_id: str
    diagnosis_id: str
    title: str
    problem_statement: str
    remediation_steps: list[str] = Field(default_factory=list)
    proposed_patches: list[RemediationPatchSpec] = Field(default_factory=list)
    verification_test_criteria: list[str] = Field(default_factory=list)
    created_at: str

class BaseFixPackageGenerator(ABC):
    """
    Contract for generating structured engineering fix packages for Coding Agents.
    The QA agent does not directly modify source code; it produces this package
    for consumption by a coding agent or engineer.
    """
    @abstractmethod
    async def generate_fix_package(self, diagnostic_report: DiagnosticReport) -> EngineeringFixPackage:
        pass
