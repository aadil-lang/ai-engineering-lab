# Engineering Lab v1 — System Architecture & Subsystem Boundaries

## 1. System Overview

**Engineering Lab v1** is a local-first, evidence-grounded engineering reliability platform that autonomously performs bounded application verification and analysis while preserving deterministic authority boundaries and human control over consequential changes.

---

## 2. End-to-End System Architecture

```text
Antigravity / Coding Agent
        ↓
Git / PR / CI
        ↓
Application Context
        ↓
Change Impact
        ↓
Regression Planning
        ↓
Engineering Lab
        ↓
Adaptive Strategy
        ↓
Playwright
        ↓
Application
        ↓
Evidence
        ↓
Deterministic Evaluation
        ↓
AI Interpretation
        ↓
Diagnosis / Remediation Proposal
        ↓
Human Governance
        ↓
Independent Retest
        ↓
Reliability + Memory
        ↓
Unified Provenance
```

---

## 3. Subsystem Authority Boundaries

Each subsystem within Engineering Lab v1 possesses explicit, non-overlapping authority:

| Subsystem | Authority & Invariant | What It May NOT Do |
| :--- | :--- | :--- |
| **Playwright Engine** | **Sole execution authority** for interacting with web application runtimes via real browser contexts. Collects multi-modal DOM, screenshot, network, and console artifacts. | Does not evaluate domain correctness or make semantic inferences. |
| **Deterministic Evaluators** | **Sole authority for behavioral contract enforcement** (e.g. 4-option schema, single correct answer exclusivity, valid status codes, schema validation). | Does not invent or guess unstated application rules. |
| **Evidence Collector** | **Sole authority for observed runtime facts**. Persists immutable snapshots, network HAR traces, performance profiles, and telemetry. | Does not synthesize speculative facts or extrapolate unobserved states. |
| **Engineering Memory** | **Authoritative repository of validated historical context** derived from past evidence. SQLite-backed with local semantic embeddings. | Current runtime evidence always overrides historical memory. Memory is never current truth. |
| **Local Hybrid RAG** | **Retrieval accelerator**, surfacing historical patterns, previous diagnoses, and remediation attempts. | RAG retrieval provides context; it has zero governance or decision authority. |
| **Local LLM / AI Agents** | **Interpretation and proposal engine**. Synthesizes diagnoses, suggests remediation fixes, and explores UI surfaces. | May NOT authorize changes, deploy code, merge pull requests, or override deterministic evaluations. |
| **Human Governance Gate** | **Sole authority for consequential changes**. Evaluates risk recommendations, inspects evidence packages, and grants cryptographically auditable authorization. | Autonomous agents cannot bypass this gate. |
| **Git / GitHub / CI** | **Authoritative version control and CI record**. Manages commits, branches, pull requests, automated linting, and unit builds. | Provenance layer references these records by SHA; it does not replace Git. |
| **Unified Provenance Layer** | **Traceability and audit integrity layer**. Chains events chronologically using SHA-256 hashes linking back to genesis. | Does not implement business logic or duplicate domain payloads. |

---

## 4. Key Execution Workflows

### 4.1 Change-Aware Testing & Adaptive Regression
When application code, prompt configurations, or contracts change:
1. `ChangeImpactEngine` determines affected components and failure risk.
2. `AdaptiveRegressionPlanner` allocates deep coverage to affected components, targeted coverage to adjacent dependencies, and smoke coverage to unaffected components.
3. `ApplicationContextService` binds runtime mode, target archetypes, and semantic state.

### 4.2 Autonomous Execution & Evidence Grounding
1. `PlaywrightTestRunner` drives headless Chromium through planned actions.
2. Every action yields verifiable evidence: DOM layouts, PNG screenshots, network requests/responses, and console logs.
3. Deterministic evaluators inspect evidence against mathematical and structural invariants.

### 4.3 Diagnosis & Remediation Loop
1. Detected failures trigger `DiagnosisService` which inspects evidence traces and retrieves relevant engineering memories.
2. `RemediationService` generates a scoped patch proposal.
3. Consequential patches require human authorization via `ChangeAuthorizationService`.
4. Fixes undergo automated CI validation and **independent retest** on a separate run ID.

---

## 5. Architectural Invariant

> **Engineering Lab v1 improves the reliability, reproducibility, observability, documentation, and demonstrability of software engineering without changing its authority boundaries or introducing new autonomous decision authority.**
