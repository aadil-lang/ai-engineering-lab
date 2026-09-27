# Slice 7.2 — Reliability Control Plane & Agent Tool Contract

## 1. System Architecture

The Reliability Control Plane provides a typed, deterministic, auditable, and transport-independent application boundary through which an autonomous QA agent interacts with the reliability platform.

The architectural boundary strictly enforces transport independence: domain logic never depends on protocol adapters such as MCP or REST.

```text
                    Autonomous QA Agent
                           |
                           v
                    Future MCP Adapter  (Slice 7.3)
                           |
                           v
                 Reliability Tool Registry
                           |
                           v
                 Reliability Control Plane
                  /       |       |       \
                 v        v       v        v
             Prediction  Failure  Evidence  Session
                 |        |       |        |
                 +--------+-------+--------+
                           |
                           v
                  Existing Reliability
                       Intelligence
                           |
             +-------------+-------------+
             |             |             |
          Playwright    Database     Evaluations
```

---

## 2. Tool Registry

The `ToolRegistry` (`backend/app/control_plane/registry.py`) acts as the single source of truth for tool declarations, schemas, execution dispatch, and transport translation.

### Registered Tools

| Tool Name | Version | Mode | Description |
| :--- | :--- | :--- | :--- |
| `inspect_application` | 1.0 | `READ_ONLY` | Inspect routes, capabilities, runtime posture, and test history. |
| `start_test_session` | 1.0 | `ACTION` | Initialize an auditable, constrained session (idempotency-protected). |
| `get_application_health` | 1.0 | `READ_ONLY` | Evaluates reliability state (`HEALTHY`, `DEGRADED`, `UNRELIABLE`, `UNKNOWN`). |
| `get_prediction` | 1.0 | `READ_ONLY` | Probabilistic failure forecast with empirical interval & training provenance. |
| `get_uncertainty` | 1.0 | `READ_ONLY` | Posterior uncertainty, covariate shift estimation, and abstention recommendation. |
| `list_failures` | 1.0 | `READ_ONLY` | Naturally observed failure catalog with cursor pagination & severity filtering. |
| `get_failure` | 1.0 | `READ_ONLY` | Deep failure telemetry, stack trace, and action replay sequence. |
| `diagnose_failure` | 1.0 | `READ_ONLY` | Multi-tier diagnosis strictly distinguishing `OBSERVED`, `INFERRED`, `HYPOTHESIZED`. |
| `get_evidence` | 1.0 | `READ_ONLY` | Redacted artifact retrieval with SHA-256 cryptographic provenance. |
| `get_reliability_summary` | 1.0 | `READ_ONLY` | High-level risk summary optimized for autonomous agent decision-making. |

### Capability Discovery
Agents discover tools dynamically via `registry.list_capabilities()`, returning version, mode, and schema signatures without hardcoded assumptions.

---

## 3. Control-Plane Responsibilities

1. **Deterministic Execution**: Given the same internal state and inputs, operations produce deterministic results.
2. **Read vs Action Separation**: Tools declare permissions (`READ_ONLY` vs `ACTION`). Read-only tools cannot mutate database state or launch agent runs. Action tools require explicit action authorization.
3. **Envelope Standardization**: Every tool execution is encapsulated within a standardized `ToolResponseEnvelope[T]`:
   - `success: bool`
   - `data: T | None`
   - `error: ToolError | None`
   - `metadata: ToolResponseMetadata` (request ID, timestamp, latency, session, provenance)
4. **Transport Decoupling**: Exposes Python callables that can be consumed directly, via FastAPI REST (`/api/tools`), or via stdio/SSE in MCP.

---

## 4. Tool Contracts

All tool requests and responses are strictly modeled using Pydantic v2 in `backend/app/models/tools.py`.

### Epistemic Separation in Diagnosis
A central invariant in `diagnose_failure` is that inferred facts must never be represented as observed truths:
* **OBSERVED**: Directly captured by Playwright telemetry, HTTP response status codes, console error strings, or DOM snapshots.
* **INFERRED**: Synthesized by deterministic analyzers or diagnostic models from observed signals.
* **HYPOTHESIZED**: Plausible mechanisms or potential race conditions requiring further validation.

---

## 5. Provenance Model

Every tool response mandates cryptographic and scientific provenance via `ToolProvenance`:
* `snapshot_id`: Immutable evaluation snapshot (`eval_snap_slice_7_1.json`).
* `model_version`: Frozen predictive model identifier (`v1.1-scaled-logistic`).
* `feature_schema_version`: Frozen temporal feature version (`v1.0-temporal`).
* `dataset_timestamp`: Precise UTC timestamp of the underlying telemetry freeze.
* `source_run_ids`: Exact run IDs contributing to the prediction or diagnosis.

A response can **never silently omit provenance**.

---

## 6. Error Model

Machine-readable typed error codes replace unstructured exception strings:

```python
class ToolErrorCode(str, Enum):
    APPLICATION_NOT_FOUND = "APPLICATION_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    FAILURE_NOT_FOUND = "FAILURE_NOT_FOUND"
    PREDICTION_NOT_FOUND = "PREDICTION_NOT_FOUND"
    EVIDENCE_NOT_FOUND = "EVIDENCE_NOT_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RELIABILITY_ABSTAINED = "RELIABILITY_ABSTAINED"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    INVALID_REQUEST = "INVALID_REQUEST"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
```

Errors are wrapped in `ToolError` containing `error_code`, `message`, `details`, and `recoverable` flag.

---

## 7. Security Boundary & Redaction Engine

The security boundary (`backend/app/control_plane/redaction.py`) guarantees that no credentials, tokens, or private secrets leave the control plane:

* **Bearer Tokens**: Redacted to `Bearer [REDACTED_TOKEN]`.
* **JWT Tokens**: RFC-7519 signatures redacted to `[REDACTED_JWT]`.
* **AWS Keys**: `AKIA...` and secret access keys redacted to `[REDACTED_AWS_KEY]`.
* **API Keys**: `sk-...` pattern matched and redacted to `[REDACTED_API_KEY]`.
* **Passwords**: Password fields in JSON and query strings redacted to `[REDACTED_PASSWORD]`.
* **Cookies**: Session cookies and auth headers stripped.
* **PEM Private Keys**: RSA/EC private keys redacted to `[REDACTED_PRIVATE_KEY]`.

The redaction engine executes recursively across dictionaries, lists, strings, and Pydantic models before any payload exits the control plane.

---

## 8. Cryptographic Audit Trail

Every invocation through `ToolRegistry.invoke()` produces an immutable audit record in `backend/app/control_plane/audit.py`:
* `event_id`: Unique identifier (`audit_...`).
* `request_id`: Tracing correlation ID.
* `tool_name` & `tool_version`.
* `actor`: Identity of the invoker (`autonomous_agent`, `developer_console`).
* `request_sha256`: SHA-256 hash of the normalized request parameters.
* `response_sha256`: SHA-256 hash of the sanitized response data.
* `result_status`: `SUCCESS` or `ERROR`.
* `error_code`: Error category if failed.
* `execution_time_ms`: Execution latency.

**Security invariant**: Audit records never store raw request or response bodies, completely preventing secondary credential leakage.

---

## 9. Versioning

Contracts adhere to semantic naming:
* Contract Version: `reliability-tools/v1`
* Tool Versions: `1.0`
* Model Version: `v1.1-scaled-logistic`
* Feature Schema: `v1.0-temporal`

Breaking changes require a major version bump and deprecation notice in `list_capabilities()`.

---

## 10. Idempotency

Action tools enforce idempotency via client-provided `idempotency_key`.

In `start_test_session`:
1. If `idempotency_key` is provided and has been previously processed, the control plane returns the existing active session record with `is_idempotent_replay=True`.
2. No duplicate background test sessions, database records, or Playwright workers are spawned.

---

## 11. Pagination

Unbounded queries (`list_failures`, future evidence listings) enforce cursor-based pagination:
* `limit`: Page size constraint (default 20, max 100).
* `cursor`: Opaque identifier of the last seen item.
* `next_cursor`: Returned cursor for subsequent fetches, or `null` when exhausted.
* `has_more`: Boolean flag.

---

## 12. MCP Adapter Boundary (Slice 7.3 Readiness)

The control plane is intentionally designed to be **MCP-ready without importing any MCP packages**:

```python
# ToolDefinition.to_mcp_tool_schema() in backend/app/control_plane/registry.py
{
    "name": tool.name,
    "description": tool.description,
    "inputSchema": tool.request_model.model_json_schema(),
    "outputSchema": tool.response_model.model_json_schema(),
    "metadata": {
        "mode": tool.mode.value,
        "version": tool.version,
        "permission_mode": tool.permission_mode
    }
}
```

The future Slice 7.3 MCP Server will simply:
1. Initialize `ReliabilityControlPlane`.
2. Query `registry.list_tools()`.
3. Expose schemas over MCP transport (stdio / SSE).
4. Dispatch incoming MCP tool calls directly into `registry.invoke()`.

---

## 13. Example Agent Interaction Sequence

```text
Autonomous QA Agent                  Reliability Control Plane
       |                                         |
       |  1. inspect_application("app_eda")     |
       |---------------------------------------->|
       |  <-- routes, capabilities, last_tested  |
       |                                         |
       |  2. get_uncertainty("app_eda")          |
       |---------------------------------------->|
       |  <-- u_width=0.18, abstention=False     |
       |                                         |
       |  3. start_test_session(mode="rel")      |
       |---------------------------------------->|
       |  <-- session_id: "sess_a89f", ACTIVE    |
       |                                         |
       |  4. list_failures(app_id="app_eda")     |
       |---------------------------------------->|
       |  <-- failures: [fail_01, fail_02]       |
       |                                         |
       |  5. diagnose_failure("fail_01")         |
       |---------------------------------------->|
       |  <-- OBSERVED: locator error            |
       |  <-- INFERRED: DOM latency race         |
       |  <-- HYPOTHESIZED: commit contention    |
```

---

## 14. Verification & Invariant Enforcement

The architecture was verified via 34 automated unit and integration tests across 8 test suites:
* `test_tool_redaction.py`: Verified zero leakage across JWT, Bearer, AWS, API keys, cookies, passwords, private keys.
* `test_tool_registry.py`: Verified capability discovery, request validation, and MCP readiness without MCP SDK.
* `test_tool_audit.py`: Verified SHA-256 request/response hash logging and zero credential storage.
* `test_tool_idempotency.py`: Verified duplicate key handling in `start_test_session`.
* `test_tool_pagination.py`: Verified cursor navigation and severity filtering.
* `test_tool_contracts.py`: Verified all 10 tools, schema validation, and epistemic fact separation.
* `test_tools_api.py`: Verified REST adapter endpoints (`/api/tools`).
* `test_control_plane.py`: Verified end-to-end lifecycle and typed error envelope conversion.

All previous scientific evaluations (Slices 6.7.2, 6.9, 7.0, 7.1) remain strictly frozen and pass with zero regressions.
