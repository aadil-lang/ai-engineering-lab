import logging
from backend.app.models.diagnosis import EngineeringDiagnosis, EvidenceBundle
from backend.app.models.enums import RunStatus
from backend.app.repositories.base import (
    RunRepositoryInterface,
    TargetRepositoryInterface,
    EvidenceRepositoryInterface,
    FailureRepositoryInterface,
    DiagnosisRepositoryInterface,
)
from backend.app.diagnosis.deterministic_analyzer import DeterministicAnalyzer
from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician
from backend.app.diagnosis.grounding_validator import DiagnosisGroundingValidator
from backend.app.core.exceptions import NotFoundException

logger = logging.getLogger("ai_qa_platform.diagnosis_service")

class DiagnosisService:
    """
    Orchestrates evidence extraction, deterministic signal analysis,
    LLM failure diagnosis generation, and independent evidence consistency validation.
    """

    def __init__(
        self,
        run_repo: RunRepositoryInterface,
        target_repo: TargetRepositoryInterface,
        evidence_repo: EvidenceRepositoryInterface,
        failure_repo: FailureRepositoryInterface,
        diagnosis_repo: DiagnosisRepositoryInterface,
        diagnostician: QwenDiagnostician | None = None,
        validator: DiagnosisGroundingValidator | None = None,
    ):
        self.run_repo = run_repo
        self.target_repo = target_repo
        self.evidence_repo = evidence_repo
        self.failure_repo = failure_repo
        self.diagnosis_repo = diagnosis_repo
        self.diagnostician = diagnostician or QwenDiagnostician()
        self.validator = validator or DiagnosisGroundingValidator()

    def diagnose_run(self, run_id: str) -> EngineeringDiagnosis:
        """Analyze evidence, generate an engineering diagnosis, and ground against evidence."""
        run = self.run_repo.get_run(run_id)
        if not run:
            raise NotFoundException(f"Test run with ID '{run_id}' not found")

        target = self.target_repo.get_target(run.application_id)
        evidence_items = self.evidence_repo.get_evidence_by_run(run_id)
        failures = self.failure_repo.get_failures_by_run(run_id)

        # 1. Deterministic Extraction
        bundle = DeterministicAnalyzer.analyze(
            run=run,
            target=target,
            evidence_items=evidence_items,
            failures=failures,
        )

        primary_failure_id = failures[0].failure_id if failures else None

        # 2. Reason & Synthesize Diagnosis (Raw from Qwen / Deterministic Fallback)
        raw_diagnosis = self.diagnostician.diagnose_failure(bundle, failure_id=primary_failure_id)

        # 3. Independent Diagnosis Grounding & Evidence Consistency Validation
        validated_diagnosis = self.validator.validate(raw_diagnosis, bundle)

        # 4. Persist Validated Diagnosis
        saved = self.diagnosis_repo.save_diagnosis(validated_diagnosis)
        return saved

    def get_run_diagnosis(self, run_id: str, auto_diagnose_if_failed: bool = True) -> EngineeringDiagnosis | None:
        """Retrieve the existing diagnosis for a run, or generate one on-the-fly if failed."""
        existing = self.diagnosis_repo.get_diagnosis_by_run(run_id)
        if existing:
            return existing

        run = self.run_repo.get_run(run_id)
        if not run:
            raise NotFoundException(f"Test run with ID '{run_id}' not found")

        if auto_diagnose_if_failed and run.status in (RunStatus.FAILED, RunStatus.ERROR):
            return self.diagnose_run(run_id)

        return None

    def list_diagnoses(self, limit: int = 50, offset: int = 0) -> list[EngineeringDiagnosis]:
        """List all recent engineering diagnoses across test runs."""
        return self.diagnosis_repo.list_diagnoses(limit=limit, offset=offset)
