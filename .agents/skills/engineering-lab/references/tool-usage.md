# Engineering Lab MCP Tool Usage Reference

This document provides detailed usage specifications, parameter schemas, response structures, and operational rules for the 10 canonical Model Context Protocol (MCP) tools provided by the Engineering Lab.

---

## 1. Tool Selection Policy

To prevent redundant RPC calls and maintain clean telemetry:

| Goal / Scenario | Recommended Tool Sequence |
| :--- | :--- |
| **New verification start** | `inspect_application` $\to$ `get_application_health` |
| **Behavioral QA run** | `start_test_session` $\to$ verify response envelope |
| **Investigating known failure** | `get_failure` $\to$ `get_evidence` $\to$ `diagnose_failure` |
| **Exploring failure history** | `list_failures` (use cursor pagination) $\to$ `get_failure` |
| **Assessing predictive risk** | `get_reliability_summary` $\to$ `get_prediction` $\to$ `get_uncertainty` |

---

## 2. Canonical Tool Catalog

### 2.1 `inspect_application`
Inspects an application target to discover its available routes, registered test cases, capabilities, and runtime posture.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "application_id": "app_inventory",
    "target_id": "real_inventory_local",
    "application_type": "crud_business",
    "base_url": "http://localhost:3002",
    "status": "ONLINE",
    "routes": ["/inventory", "/items/new", "/api/v1/inventory"],
    "test_cases": ["tc_inventory_create_edit", "tc_inventory_validation_flow"],
    "capabilities": ["CRUD_OPERATIONS", "REST_API", "DATABASE_PERSISTENCE"]
  }
  ```
* **Rules**: Do not treat route presence as proof that the route behaves correctly.

---

### 2.2 `start_test_session`
Initiates an authoritative, independent behavioral testing session in the Engineering Lab.
* **Mode**: `ACTION`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory",
    "scope": "FULL",
    "idempotency_key": "verify-inventory-v1.2-run-001",
    "timeout_seconds": 120
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "session_id": "sess-849102-a1b2",
    "application_id": "app_inventory",
    "status": "COMPLETED",
    "runs_executed": 2,
    "runs_passed": 2,
    "runs_failed": 0,
    "duration_ms": 3420,
    "idempotency_key": "verify-inventory-v1.2-run-001"
  }
  ```
* **Rules**: Always supply a unique `idempotency_key` per test attempt. Reusing an idempotency key returns the prior run record.

---

### 2.3 `get_application_health`
Retrieves the high-level operational reliability health classification of the target application.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "application_id": "app_inventory",
    "health_state": "HEALTHY",
    "recent_run_count": 25,
    "recent_pass_rate": 0.84,
    "active_incidents": 0,
    "last_executed_at": "2026-09-25T16:40:00Z"
  }
  ```
* **Rules**: Possible states are `HEALTHY`, `DEGRADED`, `UNRELIABLE`, and `UNKNOWN`. Never assume `HEALTHY` implies that no defects exist.

---

### 2.4 `get_prediction`
Forecasts the probability of failure on the next execution based on cross-application models and local calibration.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory",
    "test_case_id": "tc_inventory_validation_flow"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "probability": 0.20,
    "prediction_interval": [0.11, 0.29],
    "model_version": "v1.1-scaled-logistic",
    "feature_schema_version": "v1.0-temporal",
    "calibration_status": "CALIBRATED_K25"
  }
  ```
* **Rules**: Predictions are risk indicators, not deterministic proofs. A low probability does NOT excuse skipping verification.

---

### 2.5 `get_uncertainty`
Computes posterior uncertainty width, covariate shift, and abstention recommendations.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "posterior_interval": [0.08, 0.26],
    "uncertainty_width": 0.18,
    "evidence_count": 23,
    "covariate_shift": false,
    "abstention_recommendation": false,
    "abstention_reason": null
  }
  ```
* **Rules**: If `abstention_recommendation` is `true`, the agent MUST abstain from making definitive reliability claims and report inconclusive verification.

---

### 2.6 `list_failures`
Returns a paginated list of recorded execution failures for an application.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory",
    "limit": 10,
    "cursor": null,
    "severity": "HIGH"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "failures": [
      {
        "failure_id": "fail-901-inv-01",
        "session_id": "sess-849102-a1b2",
        "test_case_id": "tc_inventory_validation_flow",
        "error_type": "AssertionError",
        "message": "Expected status 200 but received 500",
        "timestamp": "2026-09-25T16:35:10Z"
      }
    ],
    "next_cursor": null,
    "total_available": 1
  }
  ```
* **Rules**: Always evaluate `next_cursor` to ensure pagination completeness when analyzing trend patterns.

---

### 2.7 `get_failure`
Retrieves comprehensive forensic telemetry for a specific failure instance.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "failure_id": "fail-901-inv-01"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "failure_id": "fail-901-inv-01",
    "session_id": "sess-849102-a1b2",
    "error_type": "AssertionError",
    "stack_trace": "File 'inventory_test.py', line 45, in test_validation ...",
    "step_actions": [
      {"step": 1, "action": "GOTO", "target": "/items/new", "status": "PASS"},
      {"step": 2, "action": "SUBMIT", "target": "#save-btn", "status": "FAIL"}
    ],
    "telemetry": {
      "http_status": 500,
      "latency_ms": 412
    }
  }
  ```
* **Rules**: Inspect `step_actions` to locate the exact user-interaction or API call that triggered the breakdown.

---

### 2.8 `diagnose_failure`
Synthesizes a multi-tier diagnostic attribution of the defect.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "failure_id": "fail-901-inv-01"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "failure_id": "fail-901-inv-01",
    "epistemic_analysis": {
      "observed": [
        "HTTP POST /api/v1/inventory returned HTTP 500",
        "Payload: {'item_name': '', 'quantity': -5}"
      ],
      "inferred": [
        "Backend handler lacks validation for negative quantity values"
      ],
      "hypothesized": [
        "Recent database schema update added an unsigned check constraint on quantity column"
      ]
    },
    "confidence": 0.88,
    "recommended_fix": "Add quantity >= 0 input validation in backend controller"
  }
  ```
* **Mandatory Epistemic Rule**: Never quote `HYPOTHESIZED` items as facts. Present them explicitly as candidate hypotheses requiring code inspection.

---

### 2.9 `get_evidence`
Retrieves redacted, cryptographically verified evidentiary artifacts (DOM trees, console logs, network dumps, screenshots).
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "evidence_id": "ev-8910-dom-snap"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "evidence_id": "ev-8910-dom-snap",
    "artifact_type": "DOM_SNAPSHOT",
    "sha256": "4b82c68e1a7b...489d",
    "content": "<div id='error-banner'>Internal Server Error: Invalid quantity</div>",
    "redacted": true
  }
  ```
* **Rules**: Verify the `sha256` digest when auditing historical evidence integrity.

---

### 2.10 `get_reliability_summary`
Returns high-level longitudinal risk assessment, aggregate failure concentrations, and operational stability scores.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "application_id": "app_inventory"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "application_id": "app_inventory",
    "overall_state": "MODERATE_RISK",
    "failure_rate": 0.174,
    "top_risks": [
      {
        "test_case_id": "tc_inventory_validation_flow",
        "failure_concentration": 0.50,
        "description": "Validation edge cases represent 50% of observed failures"
      }
    ],
    "historical_transitions": 23,
    "recommendations": ["Expand negative test cases for inventory creation"]
  }
  ```
* **Rules**: Use this tool to prioritize testing efforts before embarking on deep feature work.

---

### 2.11 `get_repository_status`
Retrieves current Git branch, HEAD commit SHA, parent commit SHA, clean/dirty state, and lists of changed or untracked files.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "repository_path": null
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "status": {
      "repository": "New project",
      "branch": "main",
      "commit_sha": "46d15e9e...",
      "parent_commit_sha": null,
      "is_clean": true,
      "changed_files": [],
      "untracked_files": []
    }
  }
  ```
* **Rules**: Track the exact commit SHA for every verification and test execution.

---

### 2.12 `get_git_diff`
Retrieves structured file diffs, patches, and additions/deletions counts between base and head commits.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "base_sha": "46d15e9e...",
    "head_sha": "9b12a4f0..."
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "diff": {
      "repository": "New project",
      "base_sha": "46d15e9e...",
      "head_sha": "9b12a4f0...",
      "files": [
        {
          "path": "backend/app/controllers/inventory.py",
          "status": "MODIFIED",
          "additions": 4,
          "deletions": 1,
          "patch": "@@ -12,3 +12,6 @@..."
        }
      ],
      "total_additions": 4,
      "total_deletions": 1
    }
  }
  ```

---

### 2.13 `get_commit`
Retrieves complete commit details including author, email, timestamp, parent commit SHA, and changed file paths.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "commit_sha": "HEAD"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "commit": {
      "commit_sha": "46d15e9e...",
      "parent_commit_sha": null,
      "author": "AI Engineering Lab",
      "email": "engineering-lab@antigravity.ai",
      "timestamp": "2026-09-27T06:17:00+00:00",
      "message": "feat: add inventory validation flow",
      "files_changed": ["backend/app/controllers/inventory.py"]
    }
  }
  ```

---

### 2.14 `get_pull_request`
Retrieves Pull Request metadata, branch tracking, head/base commit SHAs, lifecycle status, and associated AI code review findings.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "pr_id": "pr-001"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "pull_request": {
      "id": "pr-001",
      "repository": "New project",
      "number": 1,
      "title": "Add inventory item validation",
      "source_branch": "feature/inventory-validation",
      "target_branch": "main",
      "head_sha": "9b12a4f0...",
      "base_sha": "46d15e9e...",
      "status": "OPEN",
      "created_at": "2026-09-27T06:20:00Z",
      "updated_at": "2026-09-27T06:20:00Z"
    },
    "review": {
      "review_id": "rev-a1b2c3d4",
      "status": "APPROVED",
      "summary": "Code review completed with 0 blocking findings.",
      "findings": []
    }
  }
  ```

---

### 2.15 `get_ci_status`
Retrieves deterministic CI run execution status, test counts, logs, and artifacts for a target commit.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "commit_sha": "9b12a4f0..."
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "commit_sha": "9b12a4f0...",
    "latest_run": {
      "id": "ci-849201",
      "workflow": "pytest_unit",
      "status": "PASSED",
      "duration_ms": 1450,
      "tests_total": 8,
      "tests_passed": 8,
      "tests_failed": 0
    }
  }
  ```
* **Rules**: Deterministic CI execution cannot be overridden by agent speculation.

---

### 2.16 `get_release_readiness`
Evaluates all four gating criteria (Review, CI, Lab verification, Evidence) for release readiness.
* **Mode**: `READ_ONLY`
* **Input Parameters**:
  ```json
  {
    "commit_sha": "9b12a4f0...",
    "pr_id": "pr-001"
  }
  ```
* **Response Envelope Data**:
  ```json
  {
    "readiness": {
      "commit_sha": "9b12a4f0...",
      "pr_id": "pr-001",
      "overall_state": "READY_FOR_RELEASE",
      "review_status": "PASSED",
      "ci_status": "PASSED",
      "lab_status": "PASSED",
      "evidence_status": "PASSED",
      "blockers": [],
      "generated_at": "2026-09-27T06:25:00Z"
    }
  }
  ```
* **Rules**: `READY_FOR_RELEASE` indicates all gates passed; human approval is required before merge or deployment.

---

## 3. Structured Error Handling

When a tool call encounters an error, it returns a standard `ToolErrorPayload` inside the envelope:

| Error Code | Meaning | Agent Action |
| :--- | :--- | :--- |
| `APPLICATION_NOT_FOUND` | The specified application ID does not exist | Verify ID against `inspect_application` or app inventory |
| `SESSION_NOT_FOUND` | Session ID is unknown or expired | Initiate a new session via `start_test_session` |
| `FAILURE_NOT_FOUND` | Failure record not in database | Query `list_failures` to obtain valid failure IDs |
| `INSUFFICIENT_EVIDENCE` | Not enough data to generate reliable diagnosis | Run additional test sessions to collect telemetry |
| `RELIABILITY_ABSTAINED` | Uncertainty too high for reliable inference | Treat verification as inconclusive; do not guess |
| `UNAUTHORIZED_ACTION` | Security boundary violation | Cease request; check tool permission requirements |
| `INVALID_REQUEST` | Validation error on input parameters | Fix request schema according to this document |
