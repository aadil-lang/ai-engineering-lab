# AI Engineering Lab

> **Evidence-Grounded Autonomous Reliability Platform**

AI Engineering Lab is a local-first engineering reliability platform that autonomously performs bounded application verification and failure diagnosis using real browser automation and local LLMs. It combines deterministic behavioral contract evaluation, engineering memory with local hybrid RAG, mandatory human governance, and an append-only SHA-256 cryptographic provenance chain.

---

## 🏛️ System Architecture

```text
       Developer / Antigravity Agent
                    ↓
            Git / PR / CI Lifecycle
                    ↓
         Application Context Service
                    ↓
          Change Impact Analysis
                    ↓
         Adaptive Regression Planner
                    ↓
       Autonomous Execution (Playwright)
                    ↓
       Multi-Modal Evidence Collector
      (DOM Snapshots, Screenshots, HAR)
                    ↓
       Deterministic Contract Evaluators
                    ↓
      AI Root Cause Diagnosis Engine
                    ↓
        Remediation Proposal Engine
                    ↓
       Human Governance Gate & Audit
                    ↓
       Independent Retest & Verification
                    ↓
    Unified Cryptographic Provenance (SHA-256)
```

---

## 🎯 What Problem Does It Solve?

Modern web and AI applications suffer from non-deterministic failures, prompt regressions, semantic drift, and fragile test suites. Traditional end-to-end automation scripts break on minor layout shifts and lack diagnostic intelligence, while unregulated AI coding agents risk hallucinating conclusions, applying unverified changes directly to production, and obscuring verification traces.

The AI Engineering Lab enforces a disciplined, auditable loop: **bounded autonomous exploration and diagnosis paired with strict deterministic behavioral contracts, mandatory human governance for consequential changes, and unbroken cryptographic auditability.**

---

## ⚖️ Subsystem Authority Boundaries

In the AI Engineering Lab, authority boundaries are explicit, non-overlapping, and mathematically or procedurally enforced:

| Subsystem | Authority & Invariant | What It May NOT Do |
| :--- | :--- | :--- |
| **Playwright Engine** | **Sole execution authority** for web application runtime interactions. Captures multi-modal DOM, screenshot, network, and console artifacts. | Does not evaluate domain correctness or make semantic inferences. |
| **Deterministic Evaluators** | **Sole authority for behavioral contract enforcement** (e.g., 4-option schema, single correct answer exclusivity, valid status codes, schema validation). | Does not invent or guess unstated application rules. |
| **Evidence Collector** | **Sole authority for observed runtime facts**. Persists immutable snapshots, network HAR traces, and console logs. | Does not synthesize speculative facts or extrapolate unobserved states. |
| **Engineering Memory** | **Authoritative repository of validated historical context** derived from past evidence. SQLite-backed with local semantic embeddings. | Current runtime evidence always overrides historical memory. Memory is never current truth. |
| **Local Hybrid RAG** | **Retrieval accelerator**, surfacing historical patterns, previous diagnoses, and remediation attempts. | RAG retrieval provides context; it has zero governance or decision authority. |
| **Local LLM / AI Agents** | **Interpretation and proposal engine**. Synthesizes diagnoses, suggests remediation fixes, and explores UI surfaces. | May NOT authorize changes, deploy code, merge pull requests, or override deterministic evaluations. |
| **Human Governance Gate** | **Sole authority for consequential changes**. Evaluates risk recommendations, inspects evidence packages, and grants auditable authorization. | Autonomous agents cannot bypass this gate. |
| **Git / GitHub / CI** | **Authoritative version control and CI record**. Manages commits, branches, pull requests, automated linting, and unit builds. | Provenance layer references these records by SHA; it does not replace Git. |
| **Unified Provenance Layer** | **Traceability and audit integrity layer**. Chains events chronologically using SHA-256 hashes linking back to genesis. | Does not implement business logic or duplicate domain payloads. |

---

## 🔑 Core Capabilities

### 1. Application Context & Adaptive Strategy (Slices 8C & 8D.1)
- Binds target applications into semantic archetypes (e.g. `FORM_DRIVEN`, `WORKSPACE`, `DASHBOARD`).
- Calibrates execution depth, interaction timeouts, and exploration budgets dynamically to match target complexity.

### 2. Autonomous Browser Execution & Live Console (Slices 8B & 8D)
- Drives real headless Chromium sessions via Playwright, capturing multi-modal artifacts on disk (`data/artifacts/{run_id}/`): full DOM layouts, PNG screenshots, network HAR logs, and console error streams.
- Live testing console with real-time SSE telemetry, execution graphs, and run inspection.

### 3. Change-Aware Impact Analysis & Adaptive Regression (Slice 8K)
- Computes change blast radius across code, prompts, models, and API contracts.
- Allocates deep coverage to affected components, targeted regression to adjacent modules, and smoke tests to unaffected components rather than running static monolithic test suites.

### 4. Engineering Memory & Local Hybrid RAG (Slice 8E)
- Canonical SQLite memory store (`engineering_memories`) recording validated failure patterns, root cause diagnoses, and verified fixes.
- Local vector representations and lexical filtering for sub-millisecond context retrieval.
- Enforces invariant: **Current runtime evidence strictly overrides historical memory.**

### 5. Unified Engineering Provenance (Slice 8L)
- Append-only event store in SQLite (`engineering_lifecycle_events`) chaining 25 canonical lifecycle event types from initial request to post-change verification.
- Tamper-evident cryptographic linking:
  $$\text{event\_hash} = \text{SHA256}(\text{canonical\_payload} + \text{previous\_event\_hash})$$
- `verify_provenance_chain()` detects payload modifications (`MODIFIED_EVENT`), forged previous hashes (`INCORRECT_PREVIOUS_HASH`), or deleted events. Historical records are never mutated; corrections append as `EVENT_CORRECTION`.

### 6. Release Hardening & Diagnostics (Slice 8M)
- `EnvironmentDoctor`: 14 deterministic diagnostic probes evaluating runtime, database writability, Playwright, Chromium, local models, and token security.
- `EngineeringLabReadiness`: Distinguishes core operational readiness (`READY`, `READY_WITH_WARNINGS`, `NOT_READY`) from unconfigured optional components (`NOT_CONFIGURED`). Missing optional services never fail core platform readiness.
- Machine-readable `EngineeringLabReleaseManifest` capturing versioning, slice registries, test counts, and explicit known limitations.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLite3, pytest
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons (17 routes)
- **Browser Automation**: Playwright Python SDK (Headless Chromium)
- **Local AI / LLM Hooks**: Local Qwen 7B via Ollama (`http://localhost:11434`)
- **Protocol**: Model Context Protocol (MCP) Control Plane exposing **69 canonical agent tools**

---

## 📂 Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (runs, targets, memory, provenance, system)
│   │   ├── control_plane/   # Reliability Control Plane & MCP tool registry (69 tools)
│   │   ├── diagnosis/       # Root cause failure diagnosis engine
│   │   ├── dogfooding/      # Autonomous testing & adaptive strategy
│   │   ├── execution/       # Playwright browser runner & mock execution
│   │   ├── governance/      # Human governance approval gate & authorization
│   │   ├── memory/          # Engineering memory & local hybrid RAG
│   │   ├── provenance/      # Append-only SQLite event store & SHA-256 chain
│   │   ├── system/          # Environment doctor, readiness contract, demonstration
│   │   └── main.py          # FastAPI application entry point
│   └── tests/               # 498 total backend tests across 59 test files
├── frontend/                # Next.js 14 Dark Cyber Console (17 routes)
├── apps/                    # Target applications (Question Generator, Booking, Inventory)
├── docs/                    # Architecture, AI boundaries, runbooks, and demo scripts
└── scripts/                 # Operational startup scripts
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Chromium (via Playwright)

### Step 1: Install Dependencies
```bash
# Python backend
pip install -e .
playwright install chromium

# Next.js frontend
cd frontend
npm install
cd ..
```

### Step 2: Start the Target Application (Question Generator)
```bash
cd apps/question_generator
npm install
npm run dev
# Running on http://localhost:3000
```

### Step 3: Start the Reliability Platform Backend
```bash
python scripts/run_backend.py
# FastAPI server running on http://127.0.0.1:8000
```

### Step 4: Start the Operator Dashboard
```bash
cd frontend
npm run dev
# Dashboard accessible at http://localhost:3000 (or secondary port)
```

### Step 5: Verify Environment Readiness
```bash
curl -s http://127.0.0.1:8000/api/v1/system/readiness | jq .
```

---

## 🎬 Running the Canonical Demonstration

Execute the complete 15-phase lifecycle demonstration on the Question Generator target:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/system/demonstration/run \
  -H "Content-Type: application/json" \
  -d '{"target_id": "real_question_generator_local"}' | jq .
```

Or via automated test runner:
```bash
python -m pytest backend/tests/test_slice_8m_release_hardening.py -k test_19_canonical_demonstration_full_lifecycle -v
```

### Demonstration Lifecycle & Enforced Invariants
1. **Known-good baseline pass**: Validates 4-option math question format.
2. **Controlled candidate defect injection**: Introduces duplicate option B & C with contradictory CA tags.
3. **Deterministic contract violation**: Structural evaluator detects constraint failure.
4. **Multi-modal evidence capture**: Persists DOM snapshot and network trace.
5. **AI root cause diagnosis**: Pinpoints template deduplication failure.
6. **Remediation proposal**: Generates candidate deduplication patch.
7. **Human governance approval**: Lead QA engineer authorizes change (`HUMAN_DECISION_RECORDED`).
8. **Change authorization issuance**: Authorizes test deployment (`CHANGE_AUTHORIZED`).
9. **CI build validation**: Validates syntax and linting (`CI_COMPLETED`).
10. **Independent retest on a separate run ID**: Confirms regression resolved on a clean browser context (**Invariant: failing run is never the retest run**).
11. **Cryptographic provenance audit**: Confirms unbroken SHA-256 chain across all 17 events.

For presentation scripts and operator checklists:
- [Demo Presentation Script (3–5 min)](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/DEMO_SCRIPT.md)
- [Operator Runbook & Checklist](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/DEMO_RUNBOOK.md)

---

## 📊 Verified Repository Evidence & Metrics

All metrics and claims are derived from active code and test suites in this repository:

| Capability / Metric | Verified Source of Truth | Empirical Result |
| :--- | :--- | :--- |
| **Total Backend Test Suite** | `backend/tests/` (59 test modules) | **498 tests collected** |
| **Slice Regression Suite** | `test_slice_8c` through `test_slice_8m` | **215 / 215 tests passed (100%)** |
| **Slice 8M Dedicated Suite** | [test_slice_8m_release_hardening.py](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/backend/tests/test_slice_8m_release_hardening.py) | **44 / 44 tests passed (100%)** |
| **Slice 8L Dedicated Suite** | [test_slice_8l_engineering_provenance.py](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/backend/tests/test_slice_8l_engineering_provenance.py) | **11 / 11 tests passed (100%)** |
| **Control Plane MCP Tools** | `ReliabilityControlPlane.registry` | **69 canonical registered tools** |
| **Frontend Production Build** | Next.js 14 Production Bundle | **All 17 routes compiled clean (0 errors)** |
| **Environment Diagnostics** | `EnvironmentDoctor.run_all_checks()` | **14 deterministic probes verified** |

---

## ⚠️ Known Engineering Limitations

1. **Local Model Reasoning Bounds**: Local Qwen 7B performs structured diagnostic tasks reliably but has constrained multi-step mathematical reasoning compared to frontier cloud models.
2. **Bounded Historical Telemetry**: Dogfooding telemetry datasets are intentionally compact and focused on local test targets.
3. **Deterministic Archetype Classification**: Target categorization relies on deterministic heuristic pattern matching.
4. **Local Embedding Resolution**: Embeddings provide semantic ranking for similar error messages but do not infer deep architectural relationships.
5. **SQLite File Concurrency**: SQLite is tailored for local-first single-developer workflows; high-concurrency multi-user deployments require PostgreSQL.
6. **Development IAM**: Governance identity tokens in the local lab are designed for verification and audit trails, not multi-tenant enterprise IAM.
7. **Browser Surface**: Autonomous browser testing specializes in Chromium desktop environments.
8. **Probabilistic Diagnosis**: AI failure diagnosis is probabilistic inference; human governance remains mandatory for all consequential changes.

---

## 📚 Technical Documentation Directory

- [System Architecture & Subsystem Boundaries](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/architecture/engineering-lab.md)
- [AI Authority Boundaries](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/architecture/ai-boundaries.md)
- [Evidence Boundaries & Grounding Principles](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/architecture/evidence-boundaries.md)
- [Engineering Memory & Local Hybrid RAG Architecture](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/architecture/memory-rag.md)
- [Unified Engineering Provenance & SHA-256 Event Chaining](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/architecture/provenance.md)
- [Demo Presentation Script (3–5 min)](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/DEMO_SCRIPT.md)
- [Operator Runbook & Checklist](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/New%20project/docs/DEMO_RUNBOOK.md)
