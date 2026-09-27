from __future__ import annotations
import re
import uuid
import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.app.governance.models import EvidencePackage
from backend.app.governance.repository import GovernanceRepository
from backend.app.governance.errors import (
    EvidencePackageNotFoundError,
    EvidencePackageTamperedError,
)


def redact_secrets(text: str) -> str:
    """Scrubs API tokens, secrets, private keys, or passwords from evidence strings."""
    if not text:
        return text
    scrubbed = re.sub(
        r"(ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,}|sk-[a-zA-Z0-9]{20,})",
        "[REDACTED_SECRET]",
        text,
    )
    scrubbed = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_SECRET]", scrubbed)
    scrubbed = re.sub(r"(password|secret|token)\s*[:=]\s*['\"][^'\"]+['\"]", r"\1=[REDACTED_SECRET]", scrubbed, flags=re.IGNORECASE)
    return scrubbed


class GovernanceEvidenceService:
    """
    Constructs, scrubs, hashes, and cryptographically verifies
    canonical EvidencePackage bundles for human change governance.
    """

    def __init__(self, repo: Optional[GovernanceRepository] = None):
        self.repo = repo or GovernanceRepository()

    def create_evidence_package(
        self,
        subject_type: str,
        subject_id: str,
        git_commit_sha: Optional[str] = None,
        prompt_version: Optional[str] = None,
        model_version: Optional[str] = None,
        evaluation_snapshot_id: Optional[str] = None,
        ci_run_id: Optional[str] = None,
        lab_verification_id: Optional[str] = None,
        diagnosis_ids: Optional[List[str]] = None,
        recommendation_ids: Optional[List[str]] = None,
        observations: Optional[List[str]] = None,
        failures: Optional[List[str]] = None,
        regressions: Optional[List[str]] = None,
        verification_results: Optional[Dict[str, Any]] = None,
        package_id: Optional[str] = None,
    ) -> EvidencePackage:
        pkg_id = package_id or f"EVP-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Secret redaction
        scrubbed_obs = [redact_secrets(o) for o in (observations or [])]
        scrubbed_fails = [redact_secrets(f) for f in (failures or [])]
        scrubbed_regs = [redact_secrets(r) for r in (regressions or [])]

        raw_payload = {
            "package_id": pkg_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "git_commit_sha": git_commit_sha,
            "prompt_version": prompt_version,
            "model_version": model_version,
            "evaluation_snapshot_id": evaluation_snapshot_id,
            "ci_run_id": ci_run_id,
            "lab_verification_id": lab_verification_id,
            "diagnosis_ids": sorted(diagnosis_ids or []),
            "recommendation_ids": sorted(recommendation_ids or []),
            "observations": scrubbed_obs,
            "failures": scrubbed_fails,
            "regressions": scrubbed_regs,
            "verification_results": verification_results or {},
            "created_at": now_iso,
        }

        # Deterministic SHA-256
        content_bytes = json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        pkg = EvidencePackage(
            package_id=pkg_id,
            subject_type=subject_type,
            subject_id=subject_id,
            git_commit_sha=git_commit_sha,
            prompt_version=prompt_version,
            model_version=model_version,
            evaluation_snapshot_id=evaluation_snapshot_id,
            ci_run_id=ci_run_id,
            lab_verification_id=lab_verification_id,
            diagnosis_ids=diagnosis_ids or [],
            recommendation_ids=recommendation_ids or [],
            observations=scrubbed_obs,
            failures=scrubbed_fails,
            regressions=scrubbed_regs,
            verification_results=verification_results or {},
            created_at=now_iso,
            content_hash=content_hash,
        )

        return self.repo.save_evidence_package(pkg)

    def get_evidence_package(self, package_id: str) -> EvidencePackage:
        pkg = self.repo.get_evidence_package(package_id)
        if not pkg:
            raise EvidencePackageNotFoundError(f"Evidence package '{package_id}' not found.")
        self.verify_package_integrity(pkg)
        return pkg

    def verify_package_integrity(self, pkg: EvidencePackage) -> bool:
        """Verifies that the content hash matches the package payload."""
        raw_payload = {
            "package_id": pkg.package_id,
            "subject_type": pkg.subject_type,
            "subject_id": pkg.subject_id,
            "git_commit_sha": pkg.git_commit_sha,
            "prompt_version": pkg.prompt_version,
            "model_version": pkg.model_version,
            "evaluation_snapshot_id": pkg.evaluation_snapshot_id,
            "ci_run_id": pkg.ci_run_id,
            "lab_verification_id": pkg.lab_verification_id,
            "diagnosis_ids": sorted(pkg.diagnosis_ids),
            "recommendation_ids": sorted(pkg.recommendation_ids),
            "observations": pkg.observations,
            "failures": pkg.failures,
            "regressions": pkg.regressions,
            "verification_results": pkg.verification_results,
            "created_at": pkg.created_at,
        }
        recomputed_hash = hashlib.sha256(
            json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if recomputed_hash != pkg.content_hash:
            raise EvidencePackageTamperedError(
                f"EvidencePackage '{pkg.package_id}' hash mismatch! Expected {recomputed_hash} but found {pkg.content_hash}."
            )
        return True
