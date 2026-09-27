# Integrations: Prompt Evaluation Guide (Slice 7.7)

## 1. Overview

This guide explains how engineers, autonomous agents, and CI pipelines interact with the Prompt Reliability Lab to version, evaluate, diagnose, and compare prompts.

---

## 2. Prompt Definition & Immutable Versioning

Prompts are registered as first-class entities with semantic versioning:
* **`DRAFT`**: Work in progress. Can be refined prior to formal benchmark evaluation.
* **`EVALUATING`**: Under active benchmark evaluation.
* **`CANDIDATE`**: Version has completed benchmark evaluation and is awaiting comparison/review.
* **`PASSED`**: Evaluated version achieved all acceptance criteria across the evaluation suite.
* **`DEPLOYED`**: Promoted to active status through human sign-off.
* **`REJECTED`**: Dropped due to unacceptable regressions or safety violations.
* **`ROLLED_BACK`**: Deactivated in favor of an earlier verified version.

### Immutability Invariant
Once a prompt version is marked as evaluated, its template, variable schemas, output schemas, and components become strictly read-only. Further iterations must be created as new versions (`v+1`).

---

## 3. Evaluation Suite Creation & Freezing

Evaluation cases represent structured test inputs designed to stress test prompts:

```json
{
  "case_id": "case_warehouse_shortage_grounding",
  "category": "NORMAL",
  "severity": "CRITICAL",
  "input": {
    "issue": "Warehouse SKU 404 is out of stock in regional hub."
  },
  "expected_behavior": "Reroute order to alternate Hub B based on inventory manifest.",
  "sources": [
    {
      "source_id": "hub_manifest",
      "content": "Regional hub A is depleted; Hub B has 500 units available for automatic reroute."
    }
  ],
  "constraints": [
    "forbidden: confidential",
    "citation_required"
  ],
  "evaluation_strategy": "COMPOSITE"
}
```

Once an evaluation run is initiated on a suite version, `is_frozen` is set to `True`. Subsequent edits to cases must increment the suite version number.

---

## 4. Evaluators & Scoring Logic

The Prompt Lab executes evaluators in deterministic sequence:

1. **`JSONSchemaEvaluator`**:
   Checks valid JSON parsing and conformance against declared schema attributes and types.
2. **`RuleBasedEvaluator`**:
   Evaluates negative constraints (`forbidden: ...`), required phrases (`required_phrase: ...`), and length limits (`max_chars: ...`).
3. **`ExactMatchEvaluator`**:
   Used when literal string or canonical JSON match is intended.
4. **`CodeExecutionEvaluator`**:
   Validates AST syntax and restricts imports to safe built-ins; disallows `os`, `subprocess`, `eval`, and network operations.
5. **`SQLExecutionEvaluator`**:
   Validates SQL syntax in an in-memory SQLite sandbox; rejects destructive DDL keywords.
6. **`GroundingEvaluator`**:
   Extracts material claims from output and computes token overlap against supplied source context chunks.
7. **`SemanticJudgeEvaluator`**:
   Evaluates keyword alignment with expected behavior and reference answers without overriding deterministic checks.

---

## 5. Comparative Evaluation & Regression Detection

When evaluating a candidate prompt (`v2`) against a baseline (`v1`):
* Both versions must be evaluated over the **same frozen suite version**.
* The comparison generates:
  * Overall pass rate delta ($\Delta$)
  * Breakdown across deterministic, grounding, and semantic gates
  * Transitions for each case: `UNCHANGED`, `FIXED_FAILURE`, `NEW_PASS`, `NEW_FAILURE`, or `REGRESSION`
* Any regression on `CRITICAL` or `HIGH` severity cases triggers an explicit blocker.

---

## 6. Safety & Provenance

* **Secret Redaction**: All API keys, tokens (`ghp_...`, `Bearer ...`, `sk-...`), and passwords are automatically scrubbed from templates and outputs.
* **No Hidden Chain-of-Thought**: Hidden reasoning tokens are never requested or stored.
* **Evaluation Snapshots**: Each run generates an immutable evaluation snapshot (`eval_snap_...`) hashed with SHA-256 for auditability.
