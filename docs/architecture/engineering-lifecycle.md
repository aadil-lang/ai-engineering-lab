# Architecture: AI Engineering Lifecycle Integration (Slice 7.5)

## 1. Executive Summary

Slice 7.5 extends the AI Engineering Lab from an autonomous reliability control plane into a complete, verifiable software-development lifecycle (SDLC). It bridges Google Antigravity (as the build, reasoning, and implementation environment) with Git, Pull Requests, AI Code Review, Deterministic CI, Independent Runtime Lab Retesting, and Cryptographic Evidence Chaining.

The overarching design principle is:
> **Antigravity builds the software. Git records the change. CI verifies the code. The Engineering Lab independently verifies the running application. Evidence connects the lifecycle.**

---

## 2. Canonical Engineering Lifecycle Flow

```text
Antigravity Agent (Reasoning & Implementation)
        │
        ▼
.agents/skills/engineering-lab (Operating Procedure)
        │
        ▼
Implementation & Local Testing
        │
        ▼
Git Branch & Commit (Canonical VCS Provenance)
        │
        ▼
Pull Request & AI Code Review (Static Diff Analysis: OBSERVED / INFERRED / HYPOTHESIS)
        │
        ▼
Deterministic CI Pipeline (pytest / npm build / unit gates)
        │
        ▼
Engineering Lab Retest (Independent Runtime Behavioral Verification)
        │
        ▼
Cryptographic Evidence Recording (SHA-256 Chained Audit Artifacts)
        │
        ▼
Release Readiness Evaluation (NOT_READY / BLOCKED / READY_FOR_RELEASE)
```

### The Controlled Remediation Loop

When behavioral defects or regressions are detected by the independent Lab:
```text
Runtime Failure Detected
        │
        ▼
Cryptographic Evidence Retrieved (inspect_application / get_evidence)
        │
        ▼
Root-Cause Diagnosis Formulated (diagnose_failure: OBSERVED vs INFERRED vs HYPOTHESIZED)
        │
        ▼
Developer / Agent Remediation (Code Fix in Antigravity)
        │
        ▼
New Git Commit (New Commit SHA & Parent Provenance)
        │
        ▼
Deterministic CI Retest (Code-level gate: pytest / npm test)
        │
        ▼
Independent Lab Behavioral Retest (Agent claim alone is NEVER sufficient)
        │
        ▼
Release Readiness Certified (READY_FOR_RELEASE without auto-deploy)
```

---

## 3. Strict Non-Negotiable Architectural Invariants

1. **Antigravity remains the Build Environment:**
   No replacement IDE, orchestrator, or proprietary build engine. Antigravity plans, codes, and reasons.
2. **Engineering Lab remains the Independent Verification Authority:**
   An agent's assertion that "the bug is resolved" is never sufficient to pass a gate. The Lab independently spins up, tests, and evaluates runtime behavior.
3. **MCP remains only a Protocol Adapter:**
   All domain logic lives in `backend/app/git/`, `backend/app/lifecycle/`, and `backend/app/control_plane/`. The MCP server is strictly a transport bridge.
4. **Control Plane / ToolRegistry remains the Canonical Source of Truth:**
   All 16 lifecycle and reliability tools are registered with typed Pydantic contracts and cryptographic SHA-256 auditing.
5. **Frozen Scientific Artifacts Unmodified:**
   Prior model weights (`v1.1-scaled-logistic.json`), holdout configurations (`v1.1-app-holdout-split.json`), and evaluation snapshots (`eval_snap_slice_6_9.json`, `eval_snap_slice_7_0.json`, `eval_snap_slice_7_1.json`, `eval_snap_slice_7_3.json`) remain strictly read-only.
6. **No Autonomous Deployment or Mutation:**
   `READY_FOR_RELEASE` certifies that configured gates passed. It must **never** trigger automatic merge, production deployment, or environment mutation.
7. **Preservation of Epistemic Semantics:**
   `UNKNOWN`, `ABSTAINED`, and `INSUFFICIENT_DATA` must never be coerced into `PASS`. Inconclusive evidence keeps gates blocked or non-ready.

---

## 4. Distinct Epistemic Verification Boundaries

A common failure mode in AI-assisted development is conflating static code examination with runtime behavioral truth. Slice 7.5 explicitly enforces boundaries:

| Layer | Responsibility | Epistemic Classification | Authority Level |
| :--- | :--- | :--- | :--- |
| **AI Code Review** | Static AST and diff pattern scanning | `OBSERVED` (literal syntax), `INFERRED` (concurrency/security hazard), `HYPOTHESIS` (perf degradation) | Advisory / Quality Gate |
| **Deterministic CI** | Unit tests, builds, type checking | `PASSED` / `FAILED` (Deterministic binary execution) | Mandatory Code Gate |
| **Engineering Lab** | Dynamic runtime test session execution | `PASS`, `FAIL`, `ABSTAINED`, `INSUFFICIENT_DATA` | Authority for Behavioral Correctness |
| **Evidence Store** | Immutable audit trail & artifact hashes | `CRYPTOGRAPHIC_PROVENANCE` (SHA-256) | Audit & Auditability Authority |
| **Release Readiness** | Synthesizes all 4 gates | `NOT_READY`, `BLOCKED`, `READY_FOR_HUMAN_REVIEW`, `READY_FOR_RELEASE` | Decision Gate (Human-Mediated) |

---

## 5. Control Plane Tool Registry (22 Canonical Tools)

The control plane registry cleanly partitions into 10 reliability tools, 6 local lifecycle tools, and 6 GitHub integration tools:

### Reliability Tools (Slice 7.2 & 7.3)
1. `inspect_application` (Read)
2. `start_test_session` (Action)
3. `get_application_health` (Read)
4. `get_prediction` (Read)
5. `get_uncertainty` (Read)
6. `list_failures` (Read)
7. `get_failure` (Read)
8. `diagnose_failure` (Read)
9. `get_evidence` (Read)
10. `get_reliability_summary` (Read)

### Local Lifecycle Integration Tools (Slice 7.5)
11. `get_repository_status` (Read)
12. `get_git_diff` (Read)
13. `get_commit` (Read)
14. `get_pull_request` (Read)
15. `get_ci_status` (Read)
16. `get_release_readiness` (Read)

### GitHub Integration Tools (Slice 7.6)
17. `get_github_repository` (Read)
18. `get_github_pull_request` (Read)
19. `get_github_pull_request_diff` (Read)
20. `get_github_ci_status` (Read)
21. `get_github_checks` (Read)
22. `get_github_pr_review` (Read)

### Prompt Reliability Lab Tools (Slice 7.7)
23. `list_prompts` (Read)
24. `get_prompt` (Read)
25. `get_prompt_version` (Read)
26. `create_prompt_version` (Action)
27. `list_evaluation_suites` (Read)
28. `get_evaluation_suite` (Read)
29. `start_evaluation` (Action)
30. `get_evaluation` (Read)
31. `get_evaluation_result` (Read)
32. `compare_prompt_versions` (Read)
33. `get_prompt_regressions` (Read)
34. `get_prompt_diagnosis` (Read)
35. `get_prompt_evidence` (Read)

Zero tools provide arbitrary shell execution, database manipulation, or unvetted filesystem writes.

---

## 6. GitHub Actions CI & Stale Commit Invalidation (Slice 7.6)

In GitHub mode:
1. **GitHub Actions as CI Authority**: CI verification requires an actual completed GitHub Actions workflow run matching the PR's exact `head_commit_sha` with `conclusion == success`.
2. **Stale Commit Invalidation**: When a PR is updated with a new commit SHA:
   - Previous commit-specific verifications (CI, AI review, Lab verification) are strictly invalidated.
   - Verification results NEVER leak across commit boundaries.
3. **Idempotent PR Status Comments**: Lab evaluation results are published to PR discussions using structured, deterministic Markdown comments tagged with an HTML idempotency comment (`<!-- antigravity-idempotency: ... -->`).
4. **Human Decision Invariant**: `READY_FOR_RELEASE` indicates all gates passed on the target SHA; automated merge and automated production deployment remain strictly prohibited.

---

## 7. Interconnected Engineering Subsystems (Slice 7.7)

The AI Engineering Lab harmonizes four complementary verification pillars:

```text
┌────────────────────────────────┐         ┌────────────────────────────────┐
│      GitHub Lifecycle (7.6)    │         │     Software Reliability (7.3) │
│ - Canonical VCS provenance     │         │ - Dynamic Playwright sessions  │
│ - PR diff & static AI review   │         │ - Longitudinal failure risk    │
│ - GitHub Actions CI gates      │         │ - Natural defect observation   │
└────────────────┬───────────────┘         └────────────────┬───────────────┘
                 │                                          │
                 ▼                                          ▼
     ┌──────────────────────────────────────────────────────────┐
     │                Evidence & Cryptographic Store            │
     │ - SHA-256 audit artifacts & reproducible evaluation logs │
     │ - Strict epistemic separation: OBSERVED/INFERRED/HYPOTH  │
     └───────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
                 ┌────────────────────────────────┐
                 │  Prompt Reliability Lab (7.7)  │
                 │ - Immutable prompt versions    │
                 │ - Frozen evaluation suites     │
                 │ - Deterministic & Grounding    │
                 │ - Multi-causal attribution     │
                 │ - Regression detection         │
                 │ - Human-approved candidates    │
                 └────────────────────────────────┘
```

1. **GitHub Lifecycle**: Governs what code is proposed and whether deterministic CI checks passed.
2. **Software Reliability Lab**: Governs what the running application actually did at runtime.
3. **Prompt Reliability Lab**: Governs whether prompt versions meet structured schemas, grounding constraints, and behavioral requirements across versioned test cases without regressing.
4. **Human Governance Layer**: Enforces human decision provenance, policy evaluation, and scoped change authorizations.
5. **Engineering Evidence**: Provides immutable, mathematically reproducible proof connecting code, prompts, runs, and human decisions.

---

## 8. Human Governance & Change Authorization (Slice 7.8)

The 45 canonical agent tools across all layers are structured as follows:

| Layer | Tools | Count |
| :--- | :--- | :--- |
| **Software Reliability QA** | `inspect_application`, `start_test_session`, `get_application_health`, `get_prediction`, `get_uncertainty`, `list_failures`, `get_failure`, `diagnose_failure`, `get_evidence`, `get_reliability_summary` | 10 |
| **Git & Engineering Lifecycle** | `get_repository_status`, `get_git_diff`, `get_commit`, `get_pull_request`, `get_ci_status`, `get_release_readiness` | 6 |
| **GitHub Actions & PR** | `get_github_repository`, `get_github_pull_request`, `get_github_pull_request_diff`, `get_github_ci_status`, `get_github_checks`, `get_github_pr_review` | 6 |
| **Prompt Reliability Lab** | `list_prompts`, `get_prompt`, `get_prompt_version`, `create_prompt_version`, `list_evaluation_suites`, `get_evaluation_suite`, `start_evaluation`, `get_evaluation`, `get_evaluation_result`, `compare_prompt_versions`, `get_prompt_regressions`, `get_prompt_diagnosis`, `get_prompt_evidence` | 13 |
| **Human Governance** | `list_recommendations`, `get_recommendation`, `create_approval_request`, `get_approval_request`, `approve_change`, `reject_change`, `get_change_authorization`, `revoke_change_authorization`, `get_governance_evidence`, `get_governance_audit` | 10 |
| **Total Canonical Tools** | | **45** |

### Operating Axiom
> **AI can analyze, recommend, and verify. Humans authorize consequential change.**

