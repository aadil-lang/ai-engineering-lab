# Engineering Trace Reference & Templates

The **Engineering Trace** is the standard factual reporting structure used by Antigravity agents to document actions, tool calls, evidence, decisions, and independent verification results.

> **Transparency Policy**: Do NOT include internal model chain-of-thought or raw reasoning blocks. The trace must remain a clean, objective record of inputs, telemetry, evidence, decisions, and outcomes.

---

## 1. Standard Engineering Trace Schema

```text
======================================================================
ENGINEERING VERIFICATION TRACE
======================================================================
TASK:               <Brief description of objective>
APPLICATION:        <app_inventory | app_eda | app_booking>
TIMESTAMP:          <ISO-8601 UTC timestamp>
STATUS:             <IN_PROGRESS | VERIFIED | FAILED | INCONCLUSIVE>

1. OBSERVATION
   - Tool Invoked:   <inspect_application | get_application_health | list_failures | etc.>
   - Input Payload:  <JSON arguments provided to MCP tool>
   - Output Status:  <SUCCESS | ABSTAINED | ERROR>
   - Findings:       <Summary of telemetry or discovered application state>

2. EVIDENCE
   - Run/Session ID: <Unique execution ID>
   - Artifacts:      <Failure ID, DOM digest, HTTP status, or SHA-256 hash>
   - Epistemic Tier: <OBSERVED | INFERRED | HYPOTHESIZED>

3. INTERPRETATION & DECISION
   - Analysis:       <Why the issue occurred or why behavior is sound>
   - Decision:       <Patch required | Re-test required | Conclude verification>

4. ACTION TAKEN
   - Code Patched:   <File path and concise description of change>
   - Local Tests:    <Local test command and result (e.g., pytest 4 passed)>

5. INDEPENDENT VERIFICATION
   - Tool Invoked:   <start_test_session>
   - Idempotency:    <New unique idempotency key>
   - Outcome:        <COMPLETED: 2/2 passed, 0 failed | FAILED>
   - Evidence Hash:  <SHA-256 verification hash or session ID>
   - Final Verdict:  <VERIFIED | REMEDIATION_REQUIRED | INCONCLUSIVE>
======================================================================
```

---

## 2. Complete Trace Examples

### Example 1: Verifying a New Feature End-to-End

```text
======================================================================
ENGINEERING VERIFICATION TRACE: INVENTORY QUANTITY VALIDATION
======================================================================
TASK:               Verify non-negative constraint on inventory items
APPLICATION:        app_inventory
TIMESTAMP:          2026-09-27T11:20:00Z
STATUS:             VERIFIED

1. OBSERVATION
   - Tool Invoked:   inspect_application
   - Input Payload:  {"application_id": "app_inventory"}
   - Output Status:  SUCCESS
   - Findings:       Discovered routes ['/inventory', '/items/new'] and test cases ['tc_inventory_validation_flow'].

2. EVIDENCE
   - Run/Session ID: sess-20260927-1120-a1
   - Artifacts:      tc_inventory_validation_flow previously recorded 2 failures on negative inputs.
   - Epistemic Tier: OBSERVED

3. INTERPRETATION & DECISION
   - Analysis:       Existing inventory controller allows negative quantity submission, resulting in 500 error.
   - Decision:       Add input validation rule `quantity >= 0` and return HTTP 422 with descriptive error.

4. ACTION TAKEN
   - Code Patched:   backend/app/controllers/inventory.py (added Pydantic validator `validate_positive_qty`)
   - Local Tests:    `python -m pytest backend/tests/test_inventory.py` (5 passed in 0.8s)

5. INDEPENDENT VERIFICATION
   - Tool Invoked:   start_test_session
   - Idempotency:    verify-inv-validation-fix-001
   - Outcome:        COMPLETED (2/2 runs passed, 0 failed, duration: 1840ms)
   - Evidence Hash:  sha256:7f8a9b2c...51d9 (session log digest)
   - Final Verdict:  VERIFIED
======================================================================
```

---

### Example 2: Handling a Regressed Failure and Remediation

```text
======================================================================
ENGINEERING VERIFICATION TRACE: BOOKING DATE ORDERING REGRESSION
======================================================================
TASK:               Diagnose and resolve checkout failure in booking flow
APPLICATION:        app_booking
TIMESTAMP:          2026-09-27T11:25:00Z
STATUS:             VERIFIED

1. OBSERVATION
   - Tool Invoked:   list_failures
   - Input Payload:  {"application_id": "app_booking", "severity": "HIGH"}
   - Output Status:  SUCCESS
   - Findings:       Found failure fail-bk-8491 with error "DateValidationError: check_out before check_in".

2. EVIDENCE
   - Run/Session ID: sess-bk-7729-b4
   - Artifacts:      Failure fail-bk-8491 stack trace in booking_wizard.py line 89.
   - Epistemic Tier: OBSERVED (step 3 submitted check_out: 2026-09-01, check_in: 2026-09-05).

3. INTERPRETATION & DECISION
   - Analysis:       Frontend calendar date picker inverted start and end parameters in payload.
   - Decision:       Normalize date parameters in API request serialization.

4. ACTION TAKEN
   - Code Patched:   frontend/components/BookingCalendar.tsx (corrected key mapping on submit payload)
   - Local Tests:    `npm run test:unit` (12 passed in 1.4s)

5. INDEPENDENT VERIFICATION
   - Tool Invoked:   start_test_session
   - Idempotency:    verify-booking-calendar-fix-002
   - Outcome:        COMPLETED (1/1 run passed, 0 failed, duration: 1420ms)
   - Evidence Hash:  sha256:a1e2f3d4...998c
   - Final Verdict:  VERIFIED
======================================================================
```

---

### Example 3: Handling Epistemic Abstention Gracefully

```text
======================================================================
ENGINEERING VERIFICATION TRACE: EDA PIPELINE RELIABILITY CHECK
======================================================================
TASK:               Assess deployment readiness for new EDA algorithm
APPLICATION:        app_eda
TIMESTAMP:          2026-09-27T11:30:00Z
STATUS:             INCONCLUSIVE

1. OBSERVATION
   - Tool Invoked:   get_uncertainty
   - Input Payload:  {"application_id": "app_eda"}
   - Output Status:  ABSTAINED (RELIABILITY_ABSTAINED)
   - Findings:       Uncertainty width is 0.52 (exceeds threshold 0.35); covariate_shift: true.

2. EVIDENCE
   - Run/Session ID: N/A (Analytical Query)
   - Artifacts:      Posterior confidence interval [0.05, 0.57]; insufficient transitions ($N=4$).
   - Epistemic Tier: OBSERVED (statistical dispersion metric)

3. INTERPRETATION & DECISION
   - Analysis:       The Engineering Lab does not possess sufficient historical data on this new workflow.
   - Decision:       Abstain from claiming production reliability; schedule exploratory test sessions.

4. ACTION TAKEN
   - Code Patched:   None
   - Local Tests:    Local unit tests pass, but behavioral history is insufficient.

5. INDEPENDENT VERIFICATION
   - Tool Invoked:   N/A
   - Idempotency:    N/A
   - Outcome:        VERIFICATION_INCONCLUSIVE
   - Evidence Hash:  N/A
   - Final Verdict:  INCONCLUSIVE (Requires collecting $\ge 15$ test runs before reliability claim is valid)
======================================================================
```
