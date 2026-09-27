# Governance & Human Change Authorization Integration Guide

## 1. Overview

This document provides technical guidance for integrating the **Human Governance Layer** into engineering workflows, Prompt Lab lifecycles, and GitHub CI/CD pipelines.

---

## 2. API Endpoints

Base path: `/api/v1/governance`

### Approval Requests
- `POST /approval-requests`: Create a new formal request for consequential change.
- `GET /approval-requests`: List approval requests (optional filter `?status=PENDING`).
- `GET /approval-requests/{id}`: Retrieve approval request with associated decision, authorization, and evidence package.
- `POST /approval-requests/{id}/approve`: Authenticated human approval endpoint. Requires `X-Human-User` or `Authorization` header.
- `POST /approval-requests/{id}/reject`: Authenticated human rejection endpoint.

### Change Authorizations
- `GET /authorizations/{id}`: Retrieve authorization details, status, and expiration.
- `POST /authorizations/{id}/revoke`: Revoke an active authorization.

### Cryptographic Evidence & Audit
- `GET /evidence/{package_id}`: Retrieve and verify evidence package content hash.
- `GET /audit`: Query the append-only tamper-evident governance audit trail.

---

## 3. Workflow Examples

### A. Prompt Version Promotion Flow

```python
from backend.app.governance.models import RecommendationType, RiskLevel, DecisionType, ActorType
from backend.app.governance.approval_service import GovernanceApprovalService
from backend.app.governance.authorization_service import ChangeAuthorizationService
from backend.app.prompt_lab.prompt_service import PromptService

# 1. Create Evidence Package
pkg = evidence_service.create_evidence_package(
    subject_type="PROMPT",
    subject_id="incident-classifier",
    prompt_version="2",
    evaluation_snapshot_id="eval_snap_002",
    observations=["Evaluation suite passed with 100% schema accuracy."],
)

# 2. Request Approval
apr = approval_service.create_approval_request(
    change_type=RecommendationType.PROMPT_CHANGE,
    subject_type="PROMPT",
    subject_id="incident-classifier",
    proposed_version="2",
    evidence_package_id=pkg.package_id,
    evaluation_snapshot_id="eval_snap_002",
)

# 3. Human Approval (AI cannot call this!)
apr, decision, auth = approval_service.record_decision(
    approval_request_id=apr.approval_request_id,
    decision=DecisionType.APPROVE,
    decision_maker_id="lead_ai_engineer@enterprise.org",
    decision_reason="Confirmed zero regressions on frozen test suite.",
    actor_type=ActorType.HUMAN,
    evidence_acknowledged=True,
    version_acknowledged=True,
)

# 4. Promote Prompt
prompt_service.promote_prompt_version(
    prompt_id="incident-classifier",
    version=2,
    authorization_id=auth.authorization_id,
)
```

---

## 4. Control Plane / Tool Registry Canonical Tools (Tools 36–45)

When `enable_governance_tools=True` is configured, 10 canonical governance tools are available in `ToolRegistry`:

1. `list_recommendations` (READ_ONLY)
2. `get_recommendation` (READ_ONLY)
3. `create_approval_request` (ACTION)
4. `get_approval_request` (READ_ONLY)
5. `approve_change` (ACTION, Human only)
6. `reject_change` (ACTION, Human only)
7. `get_change_authorization` (READ_ONLY)
8. `revoke_change_authorization` (ACTION)
9. `get_governance_evidence` (READ_ONLY)
10. `get_governance_audit` (READ_ONLY)
