# AI Application Reliability & Predictive QA Platform

An autonomous, production-quality platform designed to test software and AI applications like a real user, collect multi-modal structured evidence and telemetry, diagnose failures, generate engineering remediation packages, re-test fixes, assess production readiness, and leverage historical telemetry for predictive failure and regression analysis.

---

## 🏛️ High-Level Product Architecture

The platform is architected around **4 Core Capabilities**:

```
+---------------------------------------------------------------------------------------+
|                 AI Application Reliability & Predictive QA Platform                   |
+---------------------------------------------------------------------------------------+
|  A. TEST MY APP               B. PRODUCTION READINESS    C. ENGINEERING FEEDBACK LOOP |
|  - Functional QA              - 9 Quality Dimensions     - Detect                     |
|  - Exploratory Dogfooding     - Tool Adapters:           - Evidence Collection        |
|  - UX/UI Review                 * k6 (Load & Capacity)   - Diagnosis Engine           |
|  - AI/LLM Evaluation            * OpenTelemetry          - Coding Agent Fix Package   |
|  - Regression QA                * Prometheus / Grafana   - Automated Retest & Verify  |
|                                 * OWASP ZAP (Security)                                |
|                                 * Chaos Mesh / Litmus    D. PREDICTIVE RELIABILITY    |
|                                                          - Telemetry Ingestion        |
|                                                          - Feature Engineering (ML)   |
|                                                          - Failure-Risk Prediction    |
+---------------------------------------------------------------------------------------+
```

---

## 🚀 Vertical Slice Progression

### Vertical Slice 1 — Foundation & Deterministic Mock Architecture
- Strongly typed domain models (`ApplicationTarget`, `TestRun`, `TestAction`, `Evidence`, `Failure`, `Metric`, `Assessment`).
- Pluggable abstract persistence with zero-dependency SQLite repository.
- Mock execution engine collecting simulated DOM snapshots, screenshots, network HAR, console logs.
- FastAPI REST API & Next.js 14 Dark Cyber Dashboard.

### Vertical Slice 2 — Real Playwright Browser Execution (ACTIVE)
- **Real Headless Chromium Automation**: Concrete `PlaywrightTestRunner` (`backend/app/execution/playwright_runner.py`) using `playwright.async_api`.
- **Browser Context Isolation**: Every test run creates an isolated `BrowserContext` with dedicated `session_id` and `browser_context_id`.
- **Disk-Based Artifact Storage**: Large artifacts (screenshots, full DOM trees, network JSON, console streams) are stored on disk under `data/artifacts/{run_id}/` with direct binary serving endpoints.
- **Real Multi-Modal Evidence**:
  - `SCREENSHOT`: Real PNG captures rendered in UI inspector with zoom/expand.
  - `DOM_SNAPSHOT`: Full captured HTML layout tree.
  - `NETWORK_HAR`: True HTTP request/response interception, status codes, and TTFB timings.
  - `CONSOLE_LOG`: True browser console logs and uncaught runtime exceptions.
  - `PERFORMANCE_TRACE`: Real `window.performance.timing` Core Web Vitals.
- **Deterministic Failure Classification**: Precise error categories (`NAVIGATION_TIMEOUT`, `ELEMENT_NOT_FOUND`, `ELEMENT_NOT_VISIBLE`, `ASSERTION_FAILED`, `NETWORK_ERROR`, `BROWSER_ERROR`, `EXECUTION_TIMEOUT`) without LLM speculation.
- **Engine Switcher**: Seamless runtime selection between `PLAYWRIGHT` (Real Engine) and `MOCK` (Fast Offline Engine) preserving 100% backwards compatibility.

```
+----------------+      +-------------------+      +----------------+
|    Next.js     | ---> |    FastAPI API    | ---> |  Run Manager   |
|  (Tailwind UI) |      | (Pydantic Models) |      |                |
+----------------+      +-------------------+      +----------------+
                                                           |
                                                           v
+----------------+      +-------------------+      +----------------+
|  UI Inspector  | <--- | SQLite Repository | <--- |  Mock Runner   |
|  & Diagnostics |      |   (Persistence)   |      |  (5 Actions &  |
+----------------+      +-------------------+      |   Evidence)    |
                                                   +----------------+
```

### 1. Simulated 5-Step Action Execution:
1. **Navigate**: Directs autonomous probe to target endpoint (`DOM_SNAPSHOT` & load latency metric).
2. **Locate**: Identifies interactive selectors with element bounding box calculations (`SCREENSHOT` & selector bounds).
3. **Input**: Dispatches form keystrokes & state mutation events (`CONSOLE_LOG` & event stream).
4. **Click**: Dispatches interactive user clicks & measures API latency (`NETWORK_HAR` & TTFB timing).
5. **Submit Workflow**: Evaluates transactional confirmation state (`PERFORMANCE_TRACE` / `LLM_TRANSCRIPT`).

### 2. Failure Diagnosis & Engineering Feedback Package:
When a failure occurs (or is simulated), the platform automatically:
- Categorizes failure (`ASSERTION_FAILURE`, `FUNCTIONAL_BUG`, `LLM_HALLUCINATION`, `PERF_DEGRADATION`, etc.)
- Assesses severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`)
- Extracts error stack traces and links them to exact step evidence
- Formats a **Coding-Agent Fix Package** containing a remediation specification ready for consumption by automated coding agents (e.g. Qwen2.5-Coder).

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLite3, pytest
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons
- **Storage**: Abstract Repository Pattern with concrete SQLite implementation (easily swappable with PostgreSQL)
- **Local AI / Browser Hooks**:
  - `backend/app/agents/base_agent.py` (Ready for local Qwen2.5-Coder 7B via Ollama)
  - `backend/app/execution/base_runner.py` (Ready for Playwright browser driver)
  - `backend/app/assessment/base_assessor.py` (Ready for k6, OTel, OWASP ZAP)

---

## 📂 Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints (runs, targets, test cases, assessments)
│   │   ├── core/            # Config, database connection, exception handling
│   │   ├── models/          # Strongly typed Pydantic domain models
│   │   ├── repositories/    # Abstract & SQLite repository implementations
│   │   ├── execution/       # Base runner & Deterministic Mock Runner
│   │   ├── evidence/        # Evidence collector & local blob storage
│   │   ├── services/        # RunManager, TargetService, TestCaseService
│   │   ├── agents/          # LLM Reasoning contracts (Qwen2.5-Coder / Ollama)
│   │   ├── assessment/      # Production readiness assessment interfaces (k6, OTel, ZAP)
│   │   ├── diagnosis/       # Root cause & diagnostic engine contracts
│   │   ├── remediation/     # Engineering feedback & fix package contracts
│   │   ├── telemetry/       # Telemetry collection contracts
│   │   └── prediction/      # ML dataset & feature engineering contracts
│   ├── tests/               # Pytest suite (models, repositories, mock runner, API)
│   └── pyproject.toml
├── frontend/
│   ├── app/                 # Next.js App Router (Dashboard, Run Inspector, Architecture)
│   ├── components/          # Timeline, Evidence Viewer, Diagnostics, Launch Modal, Navbar
│   ├── lib/                 # API client, utility functions
│   ├── types/               # TypeScript interfaces matching backend domain models
│   └── tailwind.config.js
├── configs/                 # Platform YAML configurations
├── data/                    # SQLite database & demo targets
├── reports/                 # Execution reports and diagnostic exports
├── scripts/                 # Startup & seeding utilities (run_backend.py, seed_demo_data.py)
├── docker/                  # Dockerfiles & docker-compose configuration
└── README.md
```

---

## 🚦 Quickstart Guide

### 1. Run the Backend

```powershell
# 1. Seed demo targets and test cases
python scripts/seed_demo_data.py

# 2. Start FastAPI server (runs on http://127.0.0.1:8000)
python scripts/run_backend.py
```

API Documentation will be accessible at: `http://127.0.0.1:8000/docs`

### 2. Run the Frontend

```powershell
cd frontend
npm install
npm run dev
```

Dashboard will be accessible at: `http://localhost:3000`

### 3. Run Automated Backend Tests

```powershell
python -m pytest backend/tests -v
```

---

## 🎯 Verification Matrix

| Capability | Vertical Slice 1 Status | Future Extension Point |
|---|---|---|
| **Test My App** | Deterministic 5-step mock runner collecting DOM, Screenshots, HAR, Logs | Playwright Browser Runner |
| **Persistence** | Abstract repository pattern + SQLite | PostgreSQL / Supabase |
| **Readiness Assessment** | 9-dimension typed domain schema + sample audits | k6, OTel, Prometheus, OWASP ZAP adapters |
| **Feedback Loop** | Diagnostic parser & Coding-agent fix package generator | Ollama Qwen2.5-Coder 7B agent loop |
| **Predictive Reliability** | Telemetry feature vector contract & extraction interface | Scikit-learn / XGBoost risk models |
