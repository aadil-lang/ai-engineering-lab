# Engineering Lab v1.0.0 — Operator Demo Runbook & Checklist

This runbook provides operators and presenters with a deterministic, step-by-step checklist to prepare, execute, and verify the Engineering Lab demonstration.

---

## 📋 Operator Pre-Flight Checklist

Complete these checks prior to presenting or recording:

- [ ] **Python Environment**: Python 3.11+ active (`python --version`).
- [ ] **Node.js Environment**: Node.js 18+ active (`node -v`).
- [ ] **Dependencies**: Python virtual environment dependencies and npm packages installed.
- [ ] **Chromium Browser**: Playwright Chromium binary installed (`playwright install chromium`).
- [ ] **Ports Available**:
  - `8000` (FastAPI Backend)
  - `3000` (Next.js Target Application / Frontend)
  - `11434` (Ollama Inference Daemon — Optional)

---

## 🚀 Startup Sequence

### Step 1: Initialize the Target Application (Terminal 1)
```bash
cd apps/question_generator
npm install
npm run dev
# Confirm: Question Generator is listening on http://localhost:3000
```

### Step 2: Start the Reliability Platform Backend (Terminal 2)
```bash
python scripts/run_backend.py
# Confirm: Uvicorn running on http://127.0.0.1:8000 (Application startup complete)
```

### Step 3: Start the Operator Dashboard (Terminal 3)
```bash
cd frontend
npm install
npm run dev
# Confirm: Dashboard running on http://localhost:3000 (or secondary port assigned by Next.js)
```

---

## 🔍 Pre-Flight Verification

Verify that the platform reports `READY` or `READY_WITH_WARNINGS`:

```bash
curl -s http://127.0.0.1:8000/api/v1/system/readiness | jq .
```

Expected Output:
```json
{
  "state": "READY",
  "summary": "All core systems and capabilities are fully operational."
}
```

---

## 🎬 Demonstration Execution

### Option A: Via REST API
Trigger the canonical demonstration with a dedicated correlation ID:
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/system/demonstration/run \
  -H "Content-Type: application/json" \
  -d '{
    "correlation_id": "demo-runbook-exec-1",
    "governor_actor_id": "lead_qa_engineer_alice",
    "target_id": "real_question_generator_local"
  }' | jq .
```

### Option B: Via Python Test Runner
Execute the verified automated demonstration test:
```bash
python -m pytest backend/tests/test_slice_8m_release_hardening.py -k test_19_canonical_demonstration_full_lifecycle -v
```

### Option C: Via Web Dashboard
1. Open `http://localhost:3000/provenance` in your browser.
2. Filter by Correlation ID `demo-runbook-exec-1`.
3. Click **"Verify Cryptographic Chain"** to confirm integrity.
4. Navigate through the 17 chronological lifecycle stages in the visual timeline.

---

## 🛡️ Verification & Audit Steps

### 1. Verify Cryptographic Provenance Integrity
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/provenance/verify \
  -H "Content-Type: application/json" \
  -d '{"correlation_id": "demo-runbook-exec-1"}' | jq .
```
- Assert: `"is_valid": true`
- Assert: `"violation_type": null`

### 2. Verify Release Manifest
```bash
curl -s http://127.0.0.1:8000/api/v1/system/manifest | jq .
```
- Assert: `"release_version": "1.0.0"`
- Assert: `"frontend_build_status": "COMPILED_CLEAN"`
- Assert: `"backend_test_status": "ALL_PASSING"`

---

## 🧹 Post-Demo Teardown

1. Stop Uvicorn backend process (`Ctrl+C` in Terminal 2).
2. Stop Frontend dev server (`Ctrl+C` in Terminal 3).
3. Stop Question Generator dev server (`Ctrl+C` in Terminal 1).
4. (Optional) Remove temporary probe tables:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('backend/data/reliability_platform.db'); conn.execute('DROP TABLE IF EXISTS _readiness_probe'); conn.commit()"
   ```
