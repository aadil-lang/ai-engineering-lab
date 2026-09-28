"""
Slice 8M — System Diagnostics, Readiness Contract & Release Manifest Models

Provides structured, deterministic models for:
1. Environment Doctor checks and diagnostic evaluation
2. Capability readiness status and platform readiness contract
3. Canonical demonstration scenario execution results
4. Machine-readable Engineering Lab v1 Release Manifest
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class CheckSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class DiagnosticCheck(BaseModel):
    """Deterministic individual diagnostic check result."""
    check_id: str
    name: str
    status: CheckStatus
    observed_value: str
    expected_value: str
    message: str
    severity: CheckSeverity


class ReadinessState(str, Enum):
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    NOT_READY = "NOT_READY"


class EngineeringLabReadiness(BaseModel):
    """
    Authoritative platform readiness contract.
    Distinguishes core operational readiness from optional unconfigured integrations.
    """
    state: ReadinessState
    summary: str
    capabilities: Dict[str, str] = Field(
        default_factory=dict,
        description="Capability name -> status (READY, READY_WITH_WARNINGS, NOT_CONFIGURED, NOT_READY)"
    )
    checks: List[DiagnosticCheck] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DemonstrationScenarioResult(BaseModel):
    """Detailed trace and verification result of the canonical end-to-end demonstration."""
    correlation_id: str
    target_id: str
    baseline_passed: bool
    defect_injected: bool
    defect_type: str
    candidate_failed_as_expected: bool
    evidence_collected: bool
    evidence_ids: List[str] = Field(default_factory=list)
    diagnosis_generated: bool
    diagnosis_root_cause: Optional[str] = None
    remediation_proposed: bool
    remediation_id: Optional[str] = None
    governance_approved: bool
    governor_actor_id: Optional[str] = None
    change_authorized: bool
    authorization_id: Optional[str] = None
    fix_applied: bool
    independent_retest_passed: bool
    retest_run_id: Optional[str] = None
    post_change_verified: bool
    lifecycle_complete: bool
    provenance_chain_valid: bool
    tamper_detected: bool
    events_recorded: int
    duration_seconds: float
    summary: str


class EngineeringLabReleaseManifest(BaseModel):
    """Machine-readable Release Manifest for Engineering Lab v1."""
    release_version: str = "1.0.0"
    schema_version: str = "1.0"
    git_commit: str = "HEAD"
    release_name: str = "Engineering Lab v1 — Hardened Release"
    system_principle: str = (
        "AI explores, diagnoses, and proposes; deterministic logic evaluates behavioral contracts; "
        "evidence is authoritative for runtime facts; humans authorize consequential changes; "
        "provenance guarantees tamper-evident traceability."
    )
    feature_slice_versions: Dict[str, str] = Field(
        default_factory=lambda: {
            "Slice 8B": "Autonomous Dogfooding E2E",
            "Slice 8C": "Context-Aware Autonomous AI Dogfooding",
            "Slice 8D": "Live Autonomous Application Testing Console",
            "Slice 8D.1": "Application-Adaptive Autonomous Testing Strategy",
            "Slice 8E": "Engineering Memory + Local Hybrid RAG",
            "Slice 8K": "Change-Aware Impact Analysis + Adaptive Regression",
            "Slice 8L": "Unified Engineering Provenance & End-to-End Change Trace",
            "Slice 8M": "Engineering Lab v1 Release Hardening & Demonstration",
        }
    )
    test_suite_counts: Dict[str, int] = Field(default_factory=dict)
    frontend_build_status: str = "COMPILED_CLEAN"
    backend_test_status: str = "ALL_PASSING"
    provenance_verification_status: str = "VERIFIED_VALID"
    environment_readiness: ReadinessState = ReadinessState.READY
    known_limitations: List[str] = Field(default_factory=list)
    generated_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
