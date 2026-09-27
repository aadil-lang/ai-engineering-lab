from abc import ABC, abstractmethod
from backend.app.models.test_run import TestRun
from backend.app.models.target import ApplicationTarget
from backend.app.models.test_case import TestCase
from backend.app.models.evidence import Evidence
from backend.app.models.failure import Failure
from backend.app.models.metric import Metric
from backend.app.models.assessment import Assessment, AssessmentFinding

class RunRepositoryInterface(ABC):
    @abstractmethod
    def create_run(self, run: TestRun) -> TestRun:
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> TestRun | None:
        pass

    @abstractmethod
    def update_run(self, run: TestRun) -> TestRun:
        pass

    @abstractmethod
    def list_runs(self, limit: int = 50, offset: int = 0, application_id: str | None = None, test_mode: str | None = None, status: str | None = None) -> list[TestRun]:
        pass

    @abstractmethod
    def count_runs(self, application_id: str | None = None, test_mode: str | None = None, status: str | None = None) -> int:
        pass

class TargetRepositoryInterface(ABC):
    @abstractmethod
    def create_target(self, target: ApplicationTarget) -> ApplicationTarget:
        pass

    @abstractmethod
    def get_target(self, target_id: str) -> ApplicationTarget | None:
        pass

    @abstractmethod
    def list_targets(self) -> list[ApplicationTarget]:
        pass

class TestCaseRepositoryInterface(ABC):
    @abstractmethod
    def create_test_case(self, test_case: TestCase) -> TestCase:
        pass

    @abstractmethod
    def get_test_case(self, test_case_id: str) -> TestCase | None:
        pass

    @abstractmethod
    def list_test_cases(self, target_id: str | None = None, test_mode: str | None = None) -> list[TestCase]:
        pass

class EvidenceRepositoryInterface(ABC):
    @abstractmethod
    def save_evidence(self, evidence: Evidence) -> Evidence:
        pass

    @abstractmethod
    def get_evidence(self, evidence_id: str) -> Evidence | None:
        pass

    @abstractmethod
    def get_evidence_by_run(self, run_id: str) -> list[Evidence]:
        pass

class FailureRepositoryInterface(ABC):
    @abstractmethod
    def save_failure(self, failure: Failure) -> Failure:
        pass

    @abstractmethod
    def get_failure(self, failure_id: str) -> Failure | None:
        pass

    @abstractmethod
    def get_failures_by_run(self, run_id: str) -> list[Failure]:
        pass

class MetricRepositoryInterface(ABC):
    @abstractmethod
    def save_metric(self, metric: Metric) -> Metric:
        pass

    @abstractmethod
    def get_metrics_by_run(self, run_id: str) -> list[Metric]:
        pass

from backend.app.models.diagnosis import EngineeringDiagnosis
from backend.app.models.remediation import (
    RemediationTask,
    CodeChange,
    RemediationAttempt,
    RegressionVerification,
)

class AssessmentRepositoryInterface(ABC):
    @abstractmethod
    def save_assessment(self, assessment: Assessment) -> Assessment:
        pass

    @abstractmethod
    def get_assessment(self, assessment_id: str) -> Assessment | None:
        pass

    @abstractmethod
    def list_assessments(self, application_id: str | None = None) -> list[Assessment]:
        pass

class DiagnosisRepositoryInterface(ABC):
    @abstractmethod
    def save_diagnosis(self, diagnosis: EngineeringDiagnosis) -> EngineeringDiagnosis:
        pass

    @abstractmethod
    def get_diagnosis(self, diagnosis_id: str) -> EngineeringDiagnosis | None:
        pass

    @abstractmethod
    def get_diagnosis_by_run(self, run_id: str) -> EngineeringDiagnosis | None:
        pass

    @abstractmethod
    def list_diagnoses(self, limit: int = 50, offset: int = 0) -> list[EngineeringDiagnosis]:
        pass

class RemediationRepositoryInterface(ABC):
    @abstractmethod
    def save_remediation_task(self, task: RemediationTask) -> RemediationTask:
        pass

    @abstractmethod
    def get_remediation_task(self, task_id: str) -> RemediationTask | None:
        pass

    @abstractmethod
    def get_remediation_tasks_by_run(self, run_id: str) -> list[RemediationTask]:
        pass

    @abstractmethod
    def list_remediation_tasks(self, limit: int = 50, offset: int = 0) -> list[RemediationTask]:
        pass

from backend.app.models.reliability import PredictionRecord

class PredictionRecordRepositoryInterface(ABC):
    @abstractmethod
    def save_prediction_record(self, record: PredictionRecord) -> PredictionRecord:
        pass

    @abstractmethod
    def get_prediction_record(self, prediction_id: str) -> PredictionRecord | None:
        pass

    @abstractmethod
    def list_prediction_records(self, test_case_id: str | None = None, status: str | None = None, limit: int = 100) -> list[PredictionRecord]:
        pass

    @abstractmethod
    def update_prediction_record(self, record: PredictionRecord) -> PredictionRecord:
        pass

    @abstractmethod
    def get_pending_predictions_for_test_case(self, test_case_id: str) -> list[PredictionRecord]:
        pass

from backend.app.models.campaign import Campaign

class CampaignRepositoryInterface(ABC):
    @abstractmethod
    def create_campaign(self, campaign: Campaign) -> Campaign:
        pass

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> Campaign | None:
        pass

    @abstractmethod
    def update_campaign(self, campaign: Campaign) -> Campaign:
        pass

    @abstractmethod
    def list_campaigns(self, limit: int = 50, offset: int = 0, target_id: str | None = None) -> list[Campaign]:
        pass

    @abstractmethod
    def count_campaigns(self, target_id: str | None = None) -> int:
        pass

    @abstractmethod
    def get_runs_by_campaign(self, campaign_id: str) -> list[TestRun]:
        pass



