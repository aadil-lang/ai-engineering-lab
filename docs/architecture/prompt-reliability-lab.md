# Architecture: Prompt Reliability Lab (Slice 7.7)

## 1. Executive Summary

Slice 7.7 extends the AI Engineering Lab from conventional application verification into the **systematic evaluation of AI application behavior**.

In modern AI engineering, treating model generation as an opaque black box or assuming every failure is a prompt failure leads to fragile, misdiagnosed systems. The Prompt Reliability Lab establishes:
1. **Prompts as Immutable Engineering Artifacts**: Prompt versions are immutable once evaluated.
2. **Multi-Causal Attribution**: Diagnoses distinguish between `PROMPT_DEFECT`, `MODEL_BEHAVIOR`, `RETRIEVAL_FAILURE`, `CONTEXT_FAILURE`, `TOOL_FAILURE`, `APPLICATION_LOGIC`, `PARSER_FAILURE`, `SCHEMA_FAILURE`, `DATA_FAILURE`, `EVALUATOR_FAILURE`, and `UNKNOWN`.
3. **Deterministic Evaluation Precedence**: Schema validation, rule constraints, and execution boundaries run before and cannot be overridden by LLM-as-a-judge evaluators.
4. **Epistemic Integrity**: `UNKNOWN` and `ABSTAINED` uncertainty states are strictly preserved; they never default or coerce into `PASS`.
5. **Regression Detection on Frozen Suites**: Benchmark test suites are versioned and frozen; comparisons between baseline and candidate prompt versions surface multidimensional differences rather than a single collapsed score.
6. **No Autonomous Production Promotion**: Candidate prompt improvements require human approval; automatic production mutations are strictly forbidden.

---

## 2. Core Operational Lifecycle

```text
Prompt Definition & Version (Immutable)
        │
        ▼
Evaluation Suite Version (Frozen Cases)
        │
        ▼
AI Application / Model Execution
        │
        ▼
Output Capture + Secret Redaction + Cryptographic Hashing
        │
        ▼
Deterministic Evaluator Layer (JSON Schema, Rules, Exact Match, Sandboxed Code/SQL)
        │
        ▼
Semantic / Grounding Evaluator Layer (Source Grounding, Semantic Judge)
        │
        ▼
Failure Classification & Multi-Layer Diagnosis (OBSERVED / INFERRED / HYPOTHESIS)
        │
        ▼
Candidate Improvement Formulated (PromptImprovementCandidate)
        │
        ▼
Regression Evaluation on Identical Frozen Suite
        │
        ▼
Human Approval Decision (Mandatory Human Sign-off)
```

---

## 3. Multi-Causal Failure Taxonomy

A failed output must never be presumed to be a prompt failure without evidence. The system categorizes causal responsibility across distinct layers:

| Causal Layer | Description | Typical Observed Evidence |
| :--- | :--- | :--- |
| `PROMPT_DEFECT` | The prompt template instructions, formatting, or negative constraints failed to guide the model. | Omitted required schema fields; ambiguous instructions. |
| `MODEL_BEHAVIOR` | The model ignored explicit, unambiguous prompt instructions. | Forbidden phrases generated despite clear negative constraints. |
| `RETRIEVAL_FAILURE` | No context or irrelevant chunks were supplied from the knowledge base. | Grounding evaluator failed due to 0 source chunks. |
| `CONTEXT_FAILURE` | Retrieved context was truncated or corrupted before entering prompt. | Token window overflow or missing crucial context chunk. |
| `TOOL_FAILURE` | Downstream tool returned execution error or timed out. | Tool error in `AIExecutionRecord.tool_usage`. |
| `APPLICATION_LOGIC` | Backend wrapper logic or data transformation raised an error. | Internal 500 error or syntax compilation failure in sandbox. |
| `PARSER_FAILURE` | Model output was not parseable as declared target format. | Invalid JSON syntax; unclosed quotes or missing braces. |
| `SCHEMA_FAILURE` | Output parsed as JSON but fields had incorrect types. | String provided where integer array was required. |
| `DATA_FAILURE` | Upstream input data was malformed, corrupted, or out of domain. | Missing input fields or unexpected binary characters. |
| `EVALUATOR_FAILURE` | The evaluator itself encountered ambiguity or exceeded domain bounds. | Evaluator explicitly returned `ABSTAINED`. |
| `UNKNOWN` | Available evidence is insufficient to attribute causality. | Unresolved contradiction without ground truth. |

---

## 4. Evaluator Architecture & Precedence

Evaluations are performed by `CompositeEvaluator` following strict hierarchical precedence:

```text
1. Deterministic Checks (JSONSchema, RuleBased, ExactMatch, CodeExecution, SQLExecution)
        │
   Failed? ──Yes──► Overall Result = FAIL (LLM judge CANNOT override)
        │
        No
        ▼
2. Grounding Evaluation (Token overlap & claim attribution against retrieved sources)
        │
   Unsupported? ──Yes──► Overall Result = FAIL or PARTIAL
        │
        No
        ▼
3. Semantic Judge (Alignment with expected behavior & reference answers)
        │
        ▼
4. Composite Synthesis (Overall Status, per-case evaluator results, confidence)
```

---

## 5. Epistemic Separation in Diagnosis

Every diagnosis distinguishes:
* **`OBSERVED`**: Direct factual observations from execution artifacts and evaluator outputs (e.g. *"Output omitted required field 'priority'"*).
* **`INFERRED`**: Logical deductions derived from observations (e.g. *"The model output diverged from declared JSON schema"*).
* **`HYPOTHESIS`**: Proposed explanatory theories (e.g. *"Prompt template lacks explicit formatting constraints; few-shot examples may resolve schema non-compliance"*).

Hypotheses are never asserted as factual observations.

---

## 6. Control Plane Tool Registry Integration (35 Canonical Tools)

The Prompt Reliability Lab introduces 13 new canonical tools into the central `ToolRegistry`:
1. `list_prompts`
2. `get_prompt`
3. `get_prompt_version`
4. `create_prompt_version`
5. `list_evaluation_suites`
6. `get_evaluation_suite`
7. `start_evaluation`
8. `get_evaluation`
9. `get_evaluation_result`
10. `compare_prompt_versions`
11. `get_prompt_regressions`
12. `get_prompt_diagnosis`
13. `get_prompt_evidence`

---

## 7. Consequential Change Authorization Gate (Slice 7.8)

In accordance with the Human Governance Layer:
* A prompt improvement candidate is strictly a **hypothesis**.
* Promoting a candidate version to active/deployed production status requires an explicit, unexpired, non-revoked `ChangeAuthorization` bound to that exact version number (`target_version == authorized_version`).
* Attempting to call `promote_prompt_version(prompt_id, version, authorization_id)` without valid authorization raises `ConsequentialChangeBlockedError`.
* Approval for version $N$ never authorizes version $N+1$.

