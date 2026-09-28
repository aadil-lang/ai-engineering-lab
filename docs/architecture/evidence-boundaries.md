# Evidence Boundaries & Grounding Principles

## Core Principle

```text
Observed Fact
    ↓
Deterministic Analysis
    ↓
Evidence Bundle
    ↓
AI Interpretation
    ↓
Grounding Validation
    ↓
Human Decision (where consequential)
```

In Engineering Lab v1, the separation between **empirical observation**, **deterministic evaluation**, and **probabilistic interpretation** is absolute.

---

## 1. Hierarchy of Information Authority

1. **Observed Fact (Authoritative Ground Truth)**:
   - Captured directly from the application runtime via Playwright, network interception, or process monitoring.
   - Examples: HTTP status code `500`, screenshot showing an error banner, console error `TypeError: Cannot read properties of undefined`, DOM containing 3 options instead of 4.
   - Facts cannot be negotiated, hallucinated, or altered.

2. **Deterministic Contract Evaluation**:
   - Deterministic algorithms that check whether observed facts comply with explicit specifications.
   - Examples: Mathematical solver verifying arithmetic correctness, schema validator checking JSON response structure, exclusivity check asserting exactly one `(CA)` tag.
   - Deterministic evaluators are authoritative over contract compliance.

3. **Evidence Bundle**:
   - An immutable, disk-persisted package combining multi-modal artifacts (DOM snapshots, PNG captures, network HAR files, console streams) stamped with run ID, timestamp, and target metadata.

4. **AI Interpretation (Probabilistic Inference)**:
   - LLM-assisted analysis of the evidence bundle to identify underlying root causes and suggest remediations.
   - **Crucial Rule**: AI interpretation is a hypothesis. It must cite specific facts in the evidence bundle. If an interpretation makes claims not grounded in the evidence, the grounding validation engine rejects it.

5. **Human Consequential Decision**:
   - Consequential changes (patch application, promotion, rollback) require human authorization based on the grounded evidence bundle.

---

## 2. Invariants Across Testing Phases

- **Evidence Separation**: Baseline run evidence is NEVER recycled or substituted as candidate evidence.
- **Retest Isolation**: A candidate test that fails cannot serve as its own retest. An independent retest must execute on a separate run ID with a distinct browser context.
- **Memory vs. Evidence**: Historical engineering memory reflects past observations; it is NOT evidence of current runtime state. Current runtime evidence strictly overrides historical memory.
