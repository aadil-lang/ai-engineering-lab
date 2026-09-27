from functools import lru_cache
from backend.app.repositories.sqlite_repository import SQLiteRepository
from backend.app.execution.mock_runner import MockTestRunner
from backend.app.execution.playwright_runner import PlaywrightTestRunner
from backend.app.execution.ai_agent_runner import AIAgentTestRunner
from backend.app.agents.ollama_agent import OllamaReasoner
from backend.app.evidence.storage import LocalEvidenceBlobStorage
from backend.app.models.enums import RunnerType
from backend.app.services.run_manager import RunManager
from backend.app.services.target_service import TargetService
from backend.app.services.test_case_service import TestCaseService

@lru_cache()
def get_repository() -> SQLiteRepository:
    return SQLiteRepository()

@lru_cache()
def get_blob_storage() -> LocalEvidenceBlobStorage:
    return LocalEvidenceBlobStorage()

@lru_cache()
def get_ollama_reasoner() -> OllamaReasoner:
    return OllamaReasoner()

def get_target_service() -> TargetService:
    repo = get_repository()
    return TargetService(repo)

def get_test_case_service() -> TestCaseService:
    repo = get_repository()
    return TestCaseService(repo)

def get_run_manager() -> RunManager:
    repo = get_repository()
    blob_storage = get_blob_storage()
    reasoner = get_ollama_reasoner()

    mock_runner = MockTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
    )
    playwright_runner = PlaywrightTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=blob_storage,
    )
    ai_agent_runner = AIAgentTestRunner(
        run_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        blob_storage=blob_storage,
        reasoner=reasoner,
    )

    return RunManager(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        metric_repo=repo,
        runners={
            RunnerType.MOCK: mock_runner,
            RunnerType.PLAYWRIGHT: playwright_runner,
            RunnerType.AI_AGENT: ai_agent_runner,
        },
    )

from fastapi import Depends
from backend.app.services.diagnosis_service import DiagnosisService
from backend.app.diagnosis.qwen_diagnostician import QwenDiagnostician

def get_diagnosis_service(
    repo: SQLiteRepository = Depends(get_repository),
) -> DiagnosisService:
    diagnostician = QwenDiagnostician()
    return DiagnosisService(
        run_repo=repo,
        target_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        diagnostician=diagnostician,
    )

from backend.app.services.remediation_service import RemediationService
from backend.app.remediation.coding_agent import BaseCodingAgent, OllamaCodingAgent

@lru_cache()
def get_coding_agent() -> BaseCodingAgent:
    return OllamaCodingAgent()

def get_remediation_service(
    repo: SQLiteRepository = Depends(get_repository),
    coding_agent: BaseCodingAgent = Depends(get_coding_agent),
    diagnosis_service: DiagnosisService = Depends(get_diagnosis_service),
    run_manager: RunManager = Depends(get_run_manager),
) -> RemediationService:
    return RemediationService(
        remediation_repo=repo,
        run_repo=repo,
        diagnosis_repo=repo,
        evidence_repo=repo,
        target_repo=repo,
        coding_agent=coding_agent,
        diagnosis_service=diagnosis_service,
        run_manager=run_manager,
    )

from backend.app.services.reliability_service import ReliabilityService
from backend.app.prediction.reliability_model import LogisticReliabilityModel

@lru_cache()
def get_reliability_model() -> LogisticReliabilityModel:
    return LogisticReliabilityModel()

def get_reliability_service(
    repo: SQLiteRepository = Depends(get_repository),
    model: LogisticReliabilityModel = Depends(get_reliability_model),
) -> ReliabilityService:
    return ReliabilityService(
        run_repo=repo,
        target_repo=repo,
        test_case_repo=repo,
        evidence_repo=repo,
        failure_repo=repo,
        diagnosis_repo=repo,
        remediation_repo=repo,
        prediction_record_repo=repo,
        model=model,
    )

from backend.app.services.campaign_service import CampaignService

def get_campaign_service(
    repo: SQLiteRepository = Depends(get_repository),
    run_manager: RunManager = Depends(get_run_manager),
) -> CampaignService:
    return CampaignService(
        campaign_repo=repo,
        run_manager=run_manager,
        target_repo=repo,
        test_case_repo=repo,
    )
