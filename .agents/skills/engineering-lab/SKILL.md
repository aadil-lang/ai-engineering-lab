---
name: engineering-lab
description: >-
  Independent engineering verification, QA, evidence retrieval, failure diagnosis,
  and reliability analysis using the Engineering Lab MCP server. Use this skill when
  validating significant feature implementations, investigating suspected regressions,
  debugging failures with independent evidence, evaluating application reliability or
  predictive risk, and completing rigorous definition-of-done verification.
---

# Engineering Lab Skill

The **Engineering Lab** is an independent verification, quality assurance, and reliability system.
Antigravity is the development, reasoning, and build environment; the Engineering Lab is the authoritative verification system.

> **Core Principle**: An agent assertion that code works is insufficient. The standard of engineering completion requires:
> $$\text{Agent Implementation} + \text{Local Tests} + \text{Independent Lab Evidence} \implies \text{Verified Completion}$$

---

## When to Use the Engineering Lab

Do **NOT** use the Engineering Lab for every minor keystroke or syntax edit. Activate and use the Lab under the following specific conditions:

1. **After Implementing Significant Features**: When functional behavior or application contracts change.
2. **Before Considering a Feature Complete**: To satisfy the independent verification requirement of the Definition of Done.
3. **When a Regression is Suspected**: To query recent failure logs, inspect execution traces, and verify whether recent runs broke existing flows.
4. **When Application Reliability is Uncertain**: To consult prior reliability models, check predictive failure probability, and inspect posterior uncertainty bounds before making operational claims.
5. **When Debugging an Existing Failure**: To retrieve deep failure telemetry, examine verified evidence artifacts (DOM, screenshots, network logs), and obtain epistemic root cause diagnoses.

### When NOT to Use the Lab
* Trivial edits (documentation typos, comment updates, formatting).
* Before local unit tests pass (never ask the Lab to verify code that fails local compilation or unit tests).
* As an arbitrary command runner or shell execution service (the Lab enforces strict security boundaries).

---

## The 12-Step Engineering Lab Workflow

```mermaid
graph TD
    A[1. Understand Task] --> B[2. Inspect Repository]
    B --> C[3. Implement Change]
    C --> D[4. Run Local Tests]
    D --> E{Local Tests Pass?}
    E -- No --> C
    E -- Yes --> F[6. Ask Engineering Lab to Verify]
    F --> G[7. Inspect Lab Evidence]
    G --> H{Lab Verification Passed?}
    H -- No --> I[8. Retrieve Failure, Evidence & Diagnose]
    I --> J[9. Fix Code]
    J --> D
    H -- Yes --> K[11. Independently Verify Through Lab]
    K --> L[12. Report Structured Evidence Trace]
```

Detailed breakdown:
1. **Understand Task**: Identify user requirements and target application (`app_inventory`, `app_eda`, `app_booking`).
2. **Inspect Repository**: Locate relevant application and backend components.
3. **Implement Change**: Apply code modifications adhering to existing codebase patterns.
4. **Run Local Tests**: Execute local pytest, unit test suites, or linters via terminal.
5. **Inspect Local Results**: Ensure 100% of unit/integration tests pass locally.
6. **Ask Engineering Lab to Verify**: Invoke `start_test_session` or `inspect_application` via MCP.
7. **Inspect Evidence**: Retrieve test run results, pass/fail status, and telemetry digests.
8. **Handle Failures**:
   - Call `get_failure` to retrieve execution actions and stack traces.
   - Call `get_evidence` to retrieve DOM dumps, screenshots, or network logs.
   - Call `diagnose_failure` to receive epistemic root cause attributions.
9. **Fix**: Address diagnosed deficiencies in code.
10. **Re-run Local Tests**: Validate fix passes local unit regression.
11. **Independently Verify**: Trigger a new test run in the Engineering Lab.
12. **Report Evidence**: Provide an evidence-first summary with an Engineering Trace.

For a comprehensive walkthrough of each phase, see the [Workflow Guide](./references/workflow.md).

---

## Canonical MCP Tool Reference

The Engineering Lab exposes 10 canonical tools via Model Context Protocol (MCP). Use them according to their specific roles:

| Tool Name | Mode | Primary Purpose | Key Agent Rule |
| :--- | :---: | :--- | :--- |
| `inspect_application` | `READ_ONLY` | Inspect routes, capabilities, runtime posture | Do not mistake metadata for proof of runtime correctness. |
| `start_test_session` | `ACTION` | Initiate behavioral verification session | Preserve returned session ID; always supply `idempotency_key`. |
| `get_application_health` | `READ_ONLY` | High-level health state (`HEALTHY`, `DEGRADED`, etc.) | High-level health is context, not a replacement for testing. |
| `get_prediction` | `READ_ONLY` | Failure probability forecast ($P(\text{fail})$) | Risk signal only—never treat predictions as proof of failure or pass. |
| `get_uncertainty` | `READ_ONLY` | Posterior uncertainty interval & abstention flags | Always inspect uncertainty alongside predictions. |
| `list_failures` | `READ_ONLY` | Query recent failure history with severity filters | Respect cursor pagination; do not assume page 1 is exhaustive. |
| `get_failure` | `READ_ONLY` | Deep failure telemetry, stack traces, replay actions | Always retrieve failure details before attempting a diagnosis. |
| `diagnose_failure` | `READ_ONLY` | Multi-tier root cause analysis | Strictly distinguish `OBSERVED`, `INFERRED`, `HYPOTHESIZED`. |
| `get_evidence` | `READ_ONLY` | Cryptographically verified (SHA-256) artifacts | Prefer direct evidence over memory or assumptions. |
| `get_reliability_summary` | `READ_ONLY` | Longitudinal application risk & defect concentration | Useful for overall risk assessment and testing prioritization. |

For schemas, arguments, and return envelopes, see the [Tool Usage Reference](./references/tool-usage.md).

---

## Mandatory Epistemic Abstention Rule

If the Engineering Lab returns:
* `status: "ABSTAINED"`
* `RELIABILITY_ABSTAINED`
* `UNKNOWN`

**You MUST NOT invent a conclusion or default to assuming the application is healthy.**

- **CORRECT**: *"The Engineering Lab does not have sufficient evidence or confidence to determine reliability for this application in the current operating regime (Uncertainty width: 0.42, Covariate shift: True). Verification remains inconclusive."*
- **INCORRECT**: *"The model did not find any failures, so the system is healthy."*

---

## Definition of "Done"

Do not conflate implementation completion with verification completion. Every task follows this state progression:

```text
[ IMPLEMENTED ] ──> [ LOCAL_TESTED ] ──> [ LAB_VERIFIED ] ──> [ EVIDENCE_RECORDED ] ──> [ COMPLETE ]
```

* An agent that only writes code is at `IMPLEMENTED`.
* An agent that passes local pytest is at `LOCAL_TESTED`.
* A task is only `COMPLETE` when independent Lab verification produces concrete evidence artifacts recorded in the trace.

---

## Evidence-First Engineering Trace

When communicating verification results to the user or recording results, follow the **Observation-Evidence-Interpretation-Action-Result** framework:

```text
Task: <Verification or fix objective>
Observation: <What was observed in the application or test output>
Evidence: <Specific run ID, HTTP status code, error snippet, or SHA-256 artifact digest>
Interpretation: <Why the failure occurred or why the feature is verified>
Action: <Code change or test action executed>
Result: <Independent verification outcome from Engineering Lab>
```

> **Note on Agent Transparency**: Do not expose internal chain-of-thought or raw reasoning blocks. Output concise, factual engineering statements backed by evidence.

For detailed templates and examples, see the [Engineering Trace Template](./references/engineering-trace.md) and [Evidence Policy](./references/evidence-policy.md).

---

## Security Boundary & Human Oversight

1. **Zero System Escapes**: The Engineering Lab MCP server strictly forbids arbitrary shell execution, raw SQL queries, direct filesystem traversal, or credentials inspection. Never attempt to use MCP tools to bypass security boundaries.
2. **Missing Capabilities**: If an operation cannot be performed via the 10 canonical tools, report `TOOL_UNAVAILABLE`.
3. **Action Authorization**: The `start_test_session` tool is an `ACTION` requiring valid idempotency keys. Any future actions affecting production systems or deployments require explicit human confirmation.

---

## Helper Scripts

Convenient Python scripts are provided in [`scripts/`](./scripts/) for interacting with the Lab from Antigravity:
* [`check_lab_health.py`](./scripts/check_lab_health.py): Validates connection to the MCP server and checks registered tools.
* [`verify_application.py`](./scripts/verify_application.py): Executes an automated verification pass for an application and outputs an Engineering Trace.
