# Integrations: Real GitHub & GitHub Actions CI Integration

## 1. Executive Summary

This guide documents the real GitHub-backed software development lifecycle integration for the AI Engineering Lab. It enables direct interaction with GitHub repositories, pull requests, unified diffs, GitHub Actions workflow runs, status checks, and PR verification comments while preserving the Engineering Lab as the authoritative runtime verification system.

---

## 2. Authentication & Environment Configuration

Configuration is loaded from environment variables rather than source code.

```bash
# GitHub Access Token (read-oriented + issue comment creation)
GITHUB_TOKEN=ghp_exampleTokenPlaceholderDoNotCommitRealSecrets

# Target GitHub Repository (owner/repo)
GITHUB_REPOSITORY=antigravity/engineering-lab

# Webhook Shared Secret for HMAC-SHA256 Signature Verification
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Optional: GitHub Enterprise API URL (defaults to https://api.github.com)
GITHUB_API_URL=https://api.github.com
```

### Security & Token Redaction Guarantees
- The `GitHubClient` and all logging filters actively redact GitHub tokens (`ghp_...`, `github_pat_...`) and bearer credentials from error messages, debug output, and trace models.
- GitHub credentials are never persisted to disk, database, or exposed in frontend responses.

---

## 3. GitHub Repository & PR Synchronization

### 3.1 Pull Request Data Model
External GitHub PR states are represented explicitly and linked to local lifecycle states:

```text
GitHubPullRequest (External Source of Truth)
        │
        ▼  pr_service.sync_pull_request()
SynchronizedPR
├── repository: "owner/repo"
├── pull_request_number: 42
├── head_branch: "feature/order-worker"
├── base_branch: "main"
├── head_commit_sha: "c012b..."
├── base_commit_sha: "main_base_000"
├── github_state: "open"
├── local_lifecycle_state: "OPEN" | "CHANGES_REQUESTED" | "APPROVED" | "CI_FAILED" | "LAB_FAILED" | "READY_FOR_RELEASE" | "BLOCKED"
├── last_verified_commit_sha: null
└── ci_verified_commit_sha: null
```

### 3.2 Invalidation on PR Update (Stale Commit Protection)
When new commits are pushed to a pull request:
1. `head_commit_sha` updates.
2. `pr_service.sync_pull_request()` detects the mismatch against `existing.head_commit_sha`.
3. All previous verification records (`last_verified_commit_sha`, `ci_verified_commit_sha`) are **immediately invalidated**.
4. The local lifecycle state resets to `OPEN`.
5. Any attempt to report or rely on previous commit verification raises `StaleCommitVerificationError`.
6. Previous successful verification **never leaks into new commits**.

---

## 4. Real PR Diff & Static AI Code Review

When a PR is evaluated:
1. `GitHubClient.get_pull_request_diff` fetches the exact raw unified diff for the PR.
2. `GitHubClient.get_pull_request_files` retrieves structured changed file additions/deletions.
3. `AICodeReviewService.review_diff` analyzes the patch across 8 categories (`BUG`, `SECURITY`, `CORRECTNESS`, `PERFORMANCE`, etc.).
4. Every finding is classified into strict epistemic tiers:
   - `OBSERVED`: Literal syntax patterns visible in the diff.
   - `INFERRED`: Logical deductions (concurrency hazards, race conditions).
   - `HYPOTHESIS`: Suspected performance or behavioral regressions.
5. If critical/high findings exist, local PR status transitions to `CHANGES_REQUESTED`; otherwise `APPROVED`.

---

## 5. GitHub Actions CI Integration Gate

The release readiness evaluator enforces strict deterministic CI verification:

$$\text{PR Head SHA} == \text{CI Head SHA} \quad \land \quad \text{Status} == \text{COMPLETED} \quad \land \quad \text{Conclusion} == \text{SUCCESS}$$

If any condition fails:
- Wrong commit SHA: Evaluates as `CI_UNVERIFIED`.
- Status is queued / in-progress: Evaluates as `PENDING`.
- Conclusion is failure / cancelled: Evaluates as `FAILED`.
- AI agents **cannot override** GitHub Actions failures.

---

## 6. Independent Engineering Lab Runtime Retest

Once GitHub Actions CI passes:
1. The Engineering Lab initiates an independent runtime test session against the live application.
2. Verified artifacts (DOM state snapshots, execution logs, failure traces) are collected and hashed with SHA-256.
3. If defects occur, `diagnose_failure` isolates root causes into observed vs inferred attributions.
4. If inconclusive or shifting distributions are detected, the Lab preserves `ABSTAINED` or `UNKNOWN`.

---

## 7. Deterministic PR Status Comments

The Engineering Lab publishes verification results back to GitHub:

```markdown
### Engineering Lab Verification Report

**Commit:** `c012b34a5e`
**CI Status:** `PASSED`
**Runtime Verification:** `PASSED`
**Release Readiness:** `READY_FOR_RELEASE`

**Evidence Artifacts:**
- `ev-fix-002`
- `ev-telemetry-003`

> *Note: Engineering Lab provides independent runtime behavioral verification. Final merge decision remains human-controlled.*
```

### Idempotency & Duplicate Prevention
- An embedded HTML comment `<!-- antigravity-idempotency: owner/repo#42#c012b34a#engineering-lab-verif -->` is tracked.
- Re-running the tool returns the existing comment rather than spamming the PR.

---

## 8. Webhook Processing

GitHub webhooks (`pull_request`, `workflow_run`, `check_run`, `push`) are received at:
`POST /api/v1/github/webhooks`

1. **HMAC Signature Check**: Validates `X-Hub-Signature-256` using `GITHUB_WEBHOOK_SECRET`. Rejects invalid signatures with HTTP 401.
2. **Delivery Idempotency**: Tracks `X-GitHub-Delivery`. Duplicate deliveries are acknowledged and skipped.
3. **No Command Execution**: Webhook payloads are strictly data inputs; no arbitrary commands or scripts are triggered from payload contents.

---

## 9. Security Boundaries & Invariants

| Invariant | Enforcement Mechanism |
| :--- | :--- |
| **No Auto-Merge** | Neither MCP nor backend contains PR merge API endpoints. Merge is human-only. |
| **No Auto-Deploy** | `READY_FOR_RELEASE` indicates gate completion; never triggers CD pipelines. |
| **No Secret Leakage** | All credentials scrubbed using `redact_secrets()`. |
| **Epistemic Integrity** | `UNKNOWN`, `ABSTAINED`, and `INSUFFICIENT_DATA` are preserved and block release. |
