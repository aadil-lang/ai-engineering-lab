import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.git.models import GitDiff, GitFileDiff
from backend.app.lifecycle.models import (
    PRReview,
    ReviewFinding,
    ReviewFindingCategory,
    FindingSeverity,
    EpistemicStatus,
    ReviewStatus,
)
from backend.app.lifecycle.repository import LifecycleRepository


class AICodeReviewService:
    """
    Service performing static AI-assisted code review on PR diffs.
    Enforces strict epistemic classification: OBSERVED vs INFERRED vs HYPOTHESIS.
    Static code review is NOT runtime failure diagnosis.
    """

    def __init__(self, repository: Optional[LifecycleRepository] = None):
        self.repo = repository or LifecycleRepository()

    def review_diff(self, pr_id: str, commit_sha: str, diff: GitDiff) -> PRReview:
        """Analyzes a GitDiff and returns structured review findings with epistemic classifications."""
        findings: list[ReviewFinding] = []

        for file_diff in diff.files:
            file_findings = self._analyze_file_diff(file_diff)
            findings.extend(file_findings)

        # Determine overall review status
        has_critical = any(f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH] for f in findings)
        status = ReviewStatus.CHANGES_REQUESTED if has_critical else ReviewStatus.APPROVED

        summary = (
            f"Code review completed across {len(diff.files)} changed files ({diff.total_additions} additions, "
            f"{diff.total_deletions} deletions). Found {len(findings)} findings."
        )

        review = PRReview(
            review_id=f"rev-{uuid.uuid4().hex[:8]}",
            pr_id=pr_id,
            commit_sha=commit_sha,
            status=status,
            summary=summary,
            findings=findings,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self.repo.save_review(review)
        return review

    def _analyze_file_diff(self, file_diff: GitFileDiff) -> list[ReviewFinding]:
        """Performs static analysis on a single file's patch."""
        findings: list[ReviewFinding] = []
        lines = file_diff.patch.splitlines()

        current_line_no = 0
        for raw_line in lines:
            if raw_line.startswith("@@"):
                # Parse chunk header: @@ -1,5 +1,6 @@
                m = re.search(r"\+(\d+)", raw_line)
                if m:
                    current_line_no = int(m.group(1)) - 1
                continue

            if not raw_line.startswith("-"):
                current_line_no += 1

            if not raw_line.startswith("+") or raw_line.startswith("+++"):
                continue

            added_content = raw_line[1:].strip()

            # Rule 1: Potential credentials or hardcoded secrets (SECURITY) -> OBSERVED (literal regex match)
            if re.search(r"(?:api_key|secret_key|password|bearer_token)\s*=\s*['\"][^'\"]{8,}['\"]", added_content, re.IGNORECASE):
                findings.append(
                    ReviewFinding(
                        file=file_diff.path,
                        line=current_line_no,
                        category=ReviewFindingCategory.SECURITY,
                        severity=FindingSeverity.CRITICAL,
                        title="Hardcoded Credential Detected",
                        description="Potential plaintext secret or token detected in source code.",
                        evidence=added_content,
                        confidence=0.95,
                        epistemic_status=EpistemicStatus.OBSERVED,
                    )
                )

            # Rule 2: Bare except block (BUG / MAINTAINABILITY) -> INFERRED
            if re.search(r"except\s*:", added_content):
                findings.append(
                    ReviewFinding(
                        file=file_diff.path,
                        line=current_line_no,
                        category=ReviewFindingCategory.BUG,
                        severity=FindingSeverity.HIGH,
                        title="Bare Exception Handler",
                        description="Catching all exceptions with a bare 'except:' can suppress KeyboardInterrupt and system exits.",
                        evidence=added_content,
                        confidence=0.90,
                        epistemic_status=EpistemicStatus.INFERRED,
                    )
                )

            # Rule 3: TODO or FIXME in production code (MAINTAINABILITY) -> OBSERVED
            if re.search(r"#\s*(?:TODO|FIXME)", added_content, re.IGNORECASE):
                findings.append(
                    ReviewFinding(
                        file=file_diff.path,
                        line=current_line_no,
                        category=ReviewFindingCategory.MAINTAINABILITY,
                        severity=FindingSeverity.LOW,
                        title="Unresolved TODO / FIXME",
                        description="Code contains unresolved task annotations.",
                        evidence=added_content,
                        confidence=0.99,
                        epistemic_status=EpistemicStatus.OBSERVED,
                    )
                )

            # Rule 4: Speculative race condition / concurrency hazard -> HYPOTHESIS
            if "global " in added_content or "threading.Thread" in added_content:
                findings.append(
                    ReviewFinding(
                        file=file_diff.path,
                        line=current_line_no,
                        category=ReviewFindingCategory.REGRESSION_RISK,
                        severity=FindingSeverity.MEDIUM,
                        title="Potential Concurrency Hazard",
                        description="Shared state mutation detected; may introduce thread-safety regression under concurrent workloads.",
                        evidence=added_content,
                        confidence=0.70,
                        epistemic_status=EpistemicStatus.HYPOTHESIS,
                    )
                )

            # Rule 5: Arbitrary command execution or eval (SECURITY) -> OBSERVED
            if re.search(r"(?:eval\(|exec\(|os\.system\()", added_content):
                findings.append(
                    ReviewFinding(
                        file=file_diff.path,
                        line=current_line_no,
                        category=ReviewFindingCategory.SECURITY,
                        severity=FindingSeverity.CRITICAL,
                        title="Arbitrary Code Execution Hazard",
                        description="Direct invocation of eval, exec, or os.system introduces remote code execution vulnerability.",
                        evidence=added_content,
                        confidence=0.98,
                        epistemic_status=EpistemicStatus.OBSERVED,
                    )
                )

        return findings
