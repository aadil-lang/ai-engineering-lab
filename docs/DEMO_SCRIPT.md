# Engineering Lab v1.0.0 — End-to-End Demonstration Script (3–5 Minutes)

**Target Audience**: Engineering Leadership, System Architects, Quality Engineers.  
**Presenter Goal**: Demonstrate how Engineering Lab v1 autonomously explores, tests, diagnoses, and traces changes while preserving strict deterministic authority boundaries and mandatory human governance over consequential actions.

---

## ⏱️ Timeline Summary

| Time | Phase | Focus |
| :--- | :--- | :--- |
| **0:00 – 0:45** | System Architecture & Invariants | Clarify that AI explores and diagnoses, while deterministic evaluators enforce contracts and humans authorize changes. |
| **0:45 – 1:30** | Pre-Flight Environment Diagnostic | Run `EnvironmentDoctor` to verify platform readiness contract. |
| **1:30 – 2:30** | Baseline & Controlled Defect Injection | Demonstrate known-good baseline pass, followed by candidate regression (duplicate option / CA exclusivity failure). |
| **2:30 – 3:30** | Evidence, Diagnosis & Human Governance | Inspect captured multi-modal evidence, review AI diagnosis, and require human approval at the Governance Gate. |
| **3:30 – 4:30** | Fix Deployment, Independent Retest & CI | Show candidate fix, automated CI validation, and a distinct, independent retest run confirming green status. |
| **4:30 – 5:00** | Cryptographic Provenance Audit | Verify SHA-256 event chain integrity across the single correlation thread from genesis to verification. |

---

## 🎭 Step-by-Step Script & Command Guide

### Phase 1: Context & Architectural Invariants (0:00 – 0:45)
**Presenter (Spoken)**:
> *"Welcome. Today we are demonstrating Engineering Lab v1. Before we run any code, let's establish our core architectural invariant: **LLM output is an input to the engineering system, never an authority over it.**
> 
> In traditional test automation, scripts are brittle and lack diagnostic context. Conversely, unconstrained AI coding agents risk hallucinating conclusions, mutating production code without authorization, and obscuring verification traces. 
> 
> The Engineering Lab solves this by pairing autonomous Playwright browser exploration with deterministic behavioral contracts, grounded AI diagnosis, mandatory human governance, and an append-only SHA-256 cryptographic provenance chain."*

---

### Phase 2: Environment Readiness Diagnostic (0:45 – 1:30)
**Presenter (Spoken)**:
> *"First, let's verify our local operating environment using the deterministic Environment Doctor."*

**Action**:
```bash
curl -s http://127.0.0.1:8000/api/v1/system/readiness | jq .
```
*(Or inspect the UI status badge at `http://localhost:3000`)*

**Expected Response**:
```json
{
  "state": "READY",
  "summary": "All core systems and capabilities are fully operational.",
  "capabilities": {
    "Browser Testing": "READY",
    "Engineering Memory": "READY",
    "Change Impact": "READY",
    "Governance": "READY",
    "Provenance": "READY",
    "MCP Control Plane": "READY"
  }
}
```
**Presenter (Spoken)**:
> *"Notice that our readiness contract distinguishes core operational readiness from optional external integrations. SQLite database accessibility, Playwright browser engine, and MCP control plane are verified ready before execution begins."*

---

### Phase 3: Baseline Pass & Controlled Defect Injection (1:30 – 2:30)
**Presenter (Spoken)**:
> *"Our demonstration target is the Question Generator application, which must strictly obey a 4-option multiple-choice contract with exactly one exclusive Correct Answer tag.
> 
> Let's launch the canonical demonstration. It first validates the known-good baseline, then introduces a controlled defect into candidate prompt logic: generating duplicate distractors with contradictory correct answer tags."*

**Action**:
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/system/demonstration/run \
  -H "Content-Type: application/json" \
  -d '{"target_id": "real_question_generator_local"}' | jq .
```

**Presenter (Spoken)**:
> *"The baseline run executed and passed all constraints. Then, the candidate ran and immediately tripped our deterministic contract evaluator. The candidate did not fail because an LLM guessed it failed; it failed because our structural validator proved that Option B and Option C were duplicate entries."*

---

### Phase 4: Grounded Evidence, Diagnosis & Human Governance (2:30 – 3:30)
**Presenter (Spoken)**:
> *"Now let's examine what the system did when the failure occurred. 
> 
> 1. Multi-modal evidence was captured: DOM layout, console stream, and network HAR.
> 2. The diagnostic engine synthesized the root cause: duplicate option generation in the candidate template.
> 3. A remediation patch was proposed.
> 
> Crucially: **Did the system autonomously apply the fix? No.** Consequential changes are strictly gated by human governance."*

**Action**:
*(Point to UI `/governance` or inspect `DemonstrationScenarioResult`)*:
```json
{
  "defect_type": "DUPLICATE_OPTION_AND_NON_EXCLUSIVE_CA",
  "candidate_failed_as_expected": true,
  "evidence_collected": true,
  "diagnosis_generated": true,
  "remediation_proposed": true,
  "governance_approved": true,
  "governor_actor_id": "lead_qa_engineer_alice",
  "change_authorized": true,
  "authorization_id": "auth_..."
}
```
**Presenter (Spoken)**:
> *"Lead QA Engineer Alice reviewed the evidence package, confirmed the diagnosis, and recorded a cryptographically signed approval. Only after authorization was granted was the candidate patch deployed to our test harness."*

---

### Phase 5: Independent Retest & CI Verification (3:30 – 4:30)
**Presenter (Spoken)**:
> *"Now we observe an essential reliability invariant: **Never reuse the failing run as the retest run.**
> 
> The platform triggered CI build validation and executed an entirely separate, independent retest run with a distinct run ID and fresh browser context.
> 
> The independent retest confirmed that the deduplication filter resolved the regression, and post-change telemetry verified normal operation."*

---

### Phase 6: Cryptographic Provenance Audit (4:30 – 5:00)
**Presenter (Spoken)**:
> *"Finally, how do we prove that none of these logs were altered post-hoc? 
> 
> Every single step—from initial request, git commit, PR, CI run, context binding, baseline execution, candidate defect, evidence capture, diagnosis, human authorization, to the independent retest—is chained together in an append-only SQLite store using SHA-256 hashes linking back to genesis."*

**Action**:
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/provenance/verify | jq .
```

**Expected Response**:
```json
{
  "is_valid": true,
  "total_events": 17,
  "verified_events": 17,
  "violation_type": null,
  "details": "All 17 events verified successfully. Cryptographic chain is intact."
}
```

**Presenter Conclusion**:
> *"The audit recomputes SHA-256 hashes across every event payload and confirms that `tamper_detected` is false and the chain is 100% valid.
> 
> In summary: Engineering Lab v1 gives engineering teams autonomous exploration and diagnosis with deterministic behavioral authority, verified human governance, and unbroken cryptographic traceability. Thank you."*
