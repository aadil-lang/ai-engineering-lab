from datetime import datetime, timezone
import uuid
from backend.app.models.evidence import Evidence
from backend.app.models.enums import EvidenceType
from backend.app.repositories.base import EvidenceRepositoryInterface

class EvidenceCollector:
    """
    Evidence Collector responsible for assembling and storing structured evidence records:
    DOM snapshots, visual representations, network HAR logs, console outputs, and LLM transcripts.
    """
    def __init__(self, repository: EvidenceRepositoryInterface):
        self.repository = repository

    def collect(
        self,
        run_id: str,
        action_id: str | None,
        evidence_type: EvidenceType,
        title: str,
        payload: dict | str | list,
        metadata: dict | None = None,
        artifact_path: str | None = None,
        mime_type: str = "application/json",
    ) -> Evidence:
        evidence = Evidence(
            evidence_id=f"evi_{uuid.uuid4().hex[:8]}",
            run_id=run_id,
            action_id=action_id,
            evidence_type=evidence_type,
            title=title,
            artifact_path=artifact_path,
            mime_type=mime_type,
            payload=payload,
            metadata=metadata or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return self.repository.save_evidence(evidence)
