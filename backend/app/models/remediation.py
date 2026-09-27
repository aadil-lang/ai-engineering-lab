from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
from backend.app.models.enums import RemediationStatus, FileChangeOperation

class FileChange(BaseModel):
    path: str
    operation: FileChangeOperation = FileChangeOperation.MODIFY
    diff: str = ""
    original_content: str | None = None
    new_content: str | None = None

class CodeChange(BaseModel):
    change_id: str = Field(default_factory=lambda: f"chg_{uuid.uuid4().hex[:8]}")
    task_id: str
    summary: str
    rationale: str
    files: list[FileChange] = Field(default_factory=list)
    diff: str = ""
    risk_notes: str | None = None
    tests_to_run: list[str] = Field(default_factory=list)
    validation_results: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RemediationAttempt(BaseModel):
    attempt_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:8]}")
    task_id: str
    attempt_number: int = 1
    status: RemediationStatus = RemediationStatus.PENDING
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None
    build_result: dict = Field(default_factory=dict)
    test_result: dict = Field(default_factory=dict)
    error_output: str | None = None

class RegressionVerification(BaseModel):
    verification_id: str = Field(default_factory=lambda: f"ver_{uuid.uuid4().hex[:8]}")
    task_id: str
    original_run_id: str
    verification_run_id: str | None = None
    status: str = "PENDING"
    failed_before: bool = True
    failed_after: bool = False
    regression_detected: bool = False
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RemediationTask(BaseModel):
    task_id: str = Field(default_factory=lambda: f"rem_{uuid.uuid4().hex[:8]}")
    run_id: str
    diagnosis_id: str
    status: RemediationStatus = RemediationStatus.PENDING
    target_repository: str = "local_workspace"
    target_branch: str = "main"
    base_commit: str = "HEAD"
    code_changes: list[CodeChange] = Field(default_factory=list)
    attempts: list[RemediationAttempt] = Field(default_factory=list)
    verifications: list[RegressionVerification] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RemediationTaskCreate(BaseModel):
    run_id: str
    diagnosis_id: str
    target_repository: str = "local_workspace"
    target_branch: str = "main"
    auto_apply: bool = False
