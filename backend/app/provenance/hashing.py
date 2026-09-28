"""
Slice 8L — Cryptographic Provenance Event Hashing

Provides deterministic serialization and SHA-256 chain calculation to ensure
tamper-evident auditability across the lifecycle.
"""

import json
import hashlib
from typing import Dict, Any

GENESIS_HASH = "0" * 64


def serialize_canonical_payload(data: Dict[str, Any]) -> str:
    """
    Serializes deterministic fields of an EngineeringLifecycleEvent into a canonical string.
    Excludes event_hash and previous_event_hash from the base payload.
    """
    canonical_dict = {
        "event_id": data.get("event_id", ""),
        "sequence_number": data.get("sequence_number", 0),
        "event_type": str(data.get("event_type", "")),
        "timestamp": data.get("timestamp", ""),
        "actor_type": str(data.get("actor_type", "")),
        "actor_id": data.get("actor_id", ""),
        "correlation_id": data.get("correlation_id", ""),
        "parent_event_id": data.get("parent_event_id") or "",
        "application_id": data.get("application_id") or "",
        "target_id": data.get("target_id") or "",
        "run_id": data.get("run_id") or "",
        "test_case_id": data.get("test_case_id") or "",
        "change_set_id": data.get("change_set_id") or "",
        "plan_id": data.get("plan_id") or "",
        "memory_id": data.get("memory_id") or "",
        "evidence_id": data.get("evidence_id") or "",
        "diagnosis_id": data.get("diagnosis_id") or "",
        "remediation_id": data.get("remediation_id") or "",
        "governance_id": data.get("governance_id") or "",
        "authorization_id": data.get("authorization_id") or "",
        "git_commit": data.get("git_commit") or "",
        "pull_request_id": data.get("pull_request_id") or "",
        "ci_run_id": data.get("ci_run_id") or "",
        "context_id": data.get("context_id") or "",
        "metadata": data.get("metadata", {}),
    }

    # Deterministic JSON representation with sorted keys and compact separators
    return json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))


def calculate_event_hash(data: Dict[str, Any], previous_hash: str) -> str:
    """
    Calculates SHA-256(canonical_payload + previous_event_hash).
    """
    canonical_str = serialize_canonical_payload(data)
    combined = canonical_str + (previous_hash or GENESIS_HASH)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
