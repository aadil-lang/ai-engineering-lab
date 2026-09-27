# Human Governance & Change Authorization Architecture

## 1. Executive Summary

The **Human Governance & Change Authorization Layer (Slice 7.8)** establishes an immutable authority boundary within the AI Engineering Lab.

> **Core Operating Principle:**  
> *AI observes, tests, evaluates, diagnoses, and proposes. Humans authorize consequential change.*  
> *The Engineering Lab is an independent verification authority. It cannot grant itself authority.*

The system autonomously analyzes behavior, runs evaluations, detects failures, and produces candidate improvements. However, no consequential change (code merge, production release, prompt promotion, model configuration alteration, tool permission expansion, or deployment) may execute without an explicit, time-bounded, version-specific, and cryptographically verified **ChangeAuthorization** granted by an authenticated human decision maker.

---

## 2. Authority Boundary & Epistemic Separation

```
Autonomous Engineering Lab Realm                     Human Authority Realm
───────────────────────────────────                  ──────────────────────
Observed Application Behavior
        ↓
Evaluation & Verification Run
        ↓
Deterministic Evaluators + LLM Judges
        ↓
Evidence Bundle (SHA-256 Hashed)
        ↓
Failure Classification & Diagnosis
(OBSERVED → INFERRED → HYPOTHESIS)
        ↓
Candidate Remediation Formulation
        ↓
Governance Recommendation
───────────────────────────────────────────────────────────────────────────
                           AUTHORITY GATEWAY
───────────────────────────────────────────────────────────────────────────
                                                     Approval Request Created
                                                               ↓
                                                     Policy Compliance Check
                                                               ↓
                                                     Human Review & Evidence
                                                               ↓
                                                     Explicit Human Decision
                                                     (APPROVE / REJECT)
                                                               ↓
                                                     Change Authorization Issued
                                                     (Bound to Exact Artifact & Hash)
───────────────────────────────────────────────────────────────────────────
Consequential Change Gate (can_apply)
        ↓
Production State Transition (DEPLOYED / MERGED)
```

### Key Invariants:
1. **AI Agents Cannot Approve:** Impersonation of human authority is forbidden. Actor type must strictly be `HUMAN`. Client requests supplying agent identities (e.g. `agent-*`, `ai-*`, `llm-*`) are deterministically rejected.
2. **Exact Version Binding:** An approval granted for Prompt `v18` does not and cannot authorize `v19`.
3. **Exact Git Commit Binding:** An approval granted for PR head commit `abc123` does not authorize new commit `def456`.
4. **Cryptographic Evidence Binding:** If the evidence bundle payload or test results change after authorization is granted, the authorization is immediately invalidated (`EvidencePackageTamperedError`).
5. **Single-Use & Time-Bounded:** Authorizations expire within a configured window (default 24 hours) and transition to `USED` once applied.
6. **Explicit Acknowledgment:** Approvals require affirmative acknowledgment of verified evidence, target version, and commit SHA.

---

## 3. Core Domain Models

### GovernanceRecommendation
An advisory proposal produced by AI or automated verification. Contains proposed action, rationale, epistemic status, and `effective_risk`. Never constitutes authorization.

### ApprovalRequest
An immutable request requiring human authorization. Encapsulates change type, subject, versions, commit SHA, evaluation snapshot ID, lab verification ID, CI verification ID, and evidence package ID.

### HumanDecision
An auditable human decision record capturing decision (`APPROVE` | `REJECT`), decision maker ID, timestamp, justification, and explicit acknowledgment checkboxes.

### ChangeAuthorization
A scoped, time-bounded credential issued upon valid approval. The gate `ChangeAuthorizationService.can_apply()` verifies 12 invariants before any consequential change is permitted.

### EvidencePackage
A canonical evidence bundle containing observations, failures, regressions, and verification results, hashed with SHA-256. Tamper-evident and immutable.

### GovernanceAuditRecord
An append-only audit trail logging every governance state transition with SHA-256 hashes.

---

## 4. Risk Classification & Policy Engine

Governance policies deterministically establish `EFFECTIVE_RISK` by taking `max(ai_proposed_risk, policy_minimum_risk)`. An AI model can never silently downgrade the risk of a consequential change.

| Change Type | Minimum Risk | Required Verifications | Approvals |
| :--- | :--- | :--- | :--- |
| `PROMPT_CHANGE` | `HIGH` | Evaluation Snapshot, Regression Evaluation | 1 Human |
| `CODE_CHANGE` | `HIGH` | CI Verification, Lab Verification | 1 Human |
| `MODEL_CONFIGURATION_CHANGE` | `HIGH` | Evaluation Snapshot | 1 Human |
| `TOOL_PERMISSION_CHANGE` | `CRITICAL` | Lab Verification, Security Sign-off | 1 Human |
| `DEPLOYMENT` | `CRITICAL` | CI Verification, Lab Verification | 1 Human |
| `ROLLBACK` | `CRITICAL` | Lab Verification | 1 Human |

---

## 5. Consequential Change Gate: `can_apply()`

Before any production state mutation executes, the system invokes:

```python
can_apply(
    change_type: RecommendationType,
    subject_id: str,
    authorization_id: str,
    target_version: Optional[str] = None,
    target_commit_sha: Optional[str] = None,
    current_evidence_package_id: Optional[str] = None,
    requested_scope: str = "PROMOTE",
) -> CanApplyResult
```

It validates:
1. Authorization existence and `ACTIVE` status (not `USED`, `EXPIRED`, or `REVOKED`).
2. Expiration timestamp (`now <= expires_at`).
3. Human decision provenance (`ActorType.HUMAN`, valid human ID).
4. Subject and change type match.
5. Scope match.
6. Target version match (`authorized_version == target_version`).
7. Target commit match (`authorized_commit_sha == target_commit_sha`).
8. Evidence package hash match (`current_hash == authorized_hash`).

The function always returns structured `CanApplyResult` with `decision=AUTHORIZED` or `decision=BLOCKED` and explicit reasons. It never returns a bare boolean.
