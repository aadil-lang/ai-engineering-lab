from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# 1. Pull Request Models
# -------------------------------------------------------------------------

class PRStatus(str, Enum):
    OPEN = "OPEN"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    CI_FAILED = "CI_FAILED"
    LAB_FAILED = "LAB_FAILED"
    READY_TO_MERGE = "READY_TO_MERGE"
    MERGED = "MERGED"
    CLOSED = "CLOSED"


class PullRequest(BaseModel):
    id: str = Field(description="Unique PR identifier, e.g. pr-101")
    repository: str
    number: int
    title: str
    description: str = ""
    source_branch: str
    target_branch: str
    head_sha: str
    base_sha: str
    status: PRStatus = PRStatus.OPEN
    created_at: str
    updated_at: str
    merged_at: Optional[str] = None
    closed_at: Optional[str] = None


# -------------------------------------------------------------------------
# 2. AI Code Review Models
# -------------------------------------------------------------------------

class ReviewFindingCategory(str, Enum):
    BUG = "BUG"
    SECURITY = "SECURITY"
    CORRECTNESS = "CORRECTNESS"
    PERFORMANCE = "PERFORMANCE"
    MAINTAINABILITY = "MAINTAINABILITY"
    TESTING = "TESTING"
    API_CONTRACT = "API_CONTRACT"
    REGRESSION_RISK = "REGRESSION_RISK"


class FindingSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    HYPOTHESIS = "HYPOTHESIS"


class ReviewFinding(BaseModel):
    file: str
    line: Optional[int] = None
    category: ReviewFindingCategory
    severity: FindingSeverity
    title: str
    description: str
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    epistemic_status: EpistemicStatus


class ReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"


class PRReview(BaseModel):
    review_id: str
    pr_id: str
    commit_sha: str
    status: ReviewStatus
    summary: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    created_at: str


# -------------------------------------------------------------------------
# 3. CI Integration Models
# -------------------------------------------------------------------------

class CIStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CIRun(BaseModel):
    id: str
    commit_sha: str
    workflow: str  # e.g. "pytest", "npm_test", "build", "full_ci"
    status: CIStatus
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: int = 0
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    artifacts: list[str] = Field(default_factory=list)
    logs: str = ""


# -------------------------------------------------------------------------
# 4. Release Readiness Models
# -------------------------------------------------------------------------

class ReadinessState(str, Enum):
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    READY_FOR_RELEASE = "READY_FOR_RELEASE"


class GateStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PENDING = "PENDING"
    ABSTAINED = "ABSTAINED"
    SKIPPED = "SKIPPED"


class ReleaseReadiness(BaseModel):
    commit_sha: str
    pr_id: Optional[str] = None
    overall_state: ReadinessState
    review_status: GateStatus
    ci_status: GateStatus
    lab_status: GateStatus
    evidence_status: GateStatus
    blockers: list[str] = Field(default_factory=list)
    generated_at: str
