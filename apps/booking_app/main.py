import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Autonomous QA Dispatch & Certification Booking",
    description="Stateful multi-step booking and certification workflow engine for engineering test suites.",
    version="1.0.0",
)

class BookingRequest(BaseModel):
    service_tier: str
    customer_name: str
    customer_email: str
    scheduled_date: str
    facility: str
    expedited_qa: bool = False
    audit_log: bool = False
    notes: Optional[str] = None

class BookingRecord(BaseModel):
    booking_id: str
    reference_code: str
    service_tier: str
    customer_name: str
    customer_email: str
    scheduled_date: str
    facility: str
    expedited_qa: bool
    audit_log: bool
    total_cost: float
    status: str = "CONFIRMED"

BOOKINGS_DB: dict[str, BookingRecord] = {}

TIERS = {
    "standard": {"name": "Standard Calibration", "price": 150.0},
    "priority": {"name": "Priority QA & Stress Certification", "price": 350.0},
    "enterprise": {"name": "Enterprise Multi-Axis Inspection", "price": 800.0},
}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Autonomous QA Dispatch & Certification Booking",
        "version": "1.0.0",
        "total_bookings": len(BOOKINGS_DB),
    }

@app.get("/api/tiers")
def list_tiers():
    return TIERS

@app.get("/api/bookings")
def list_bookings():
    return list(BOOKINGS_DB.values())

@app.get("/api/bookings/{reference_code}")
def get_booking(reference_code: str):
    if reference_code not in BOOKINGS_DB:
        raise HTTPException(status_code=404, detail=f"Booking '{reference_code}' not found")
    return BOOKINGS_DB[reference_code]

@app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(req: BookingRequest):
    tier_key = req.service_tier.lower()
    if tier_key not in TIERS:
        raise HTTPException(status_code=422, detail="Invalid service tier selected")
    if not req.customer_name.strip():
        raise HTTPException(status_code=422, detail="Customer name is required")
    if "@" not in req.customer_email or "." not in req.customer_email:
        raise HTTPException(status_code=422, detail="Valid customer email is required")
    if not req.scheduled_date.strip():
        raise HTTPException(status_code=422, detail="Scheduled date is required")

    base_price = TIERS[tier_key]["price"]
    addon_price = (75.0 if req.expedited_qa else 0.0) + (50.0 if req.audit_log else 0.0)
    total_cost = base_price + addon_price

    ref_code = f"BK-{uuid.uuid4().hex[:6].upper()}"
    booking_id = f"book_{uuid.uuid4().hex[:8]}"

    record = BookingRecord(
        booking_id=booking_id,
        reference_code=ref_code,
        service_tier=TIERS[tier_key]["name"],
        customer_name=req.customer_name.strip(),
        customer_email=req.customer_email.strip(),
        scheduled_date=req.scheduled_date.strip(),
        facility=req.facility.strip() or "Main Lab - Boston",
        expedited_qa=req.expedited_qa,
        audit_log=req.audit_log,
        total_cost=total_cost,
        status="CONFIRMED",
    )
    BOOKINGS_DB[ref_code] = record
    return record

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Autonomous QA Dispatch & Certification Booking</title>
  <style>
    :root {
      --bg-dark: #090d16;
      --card-bg: #131c2e;
      --border-color: #1e2d4a;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --accent: #8b5cf6;
      --success: #10b981;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 2.5rem;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .wizard-container {
      width: 100%;
      max-width: 680px;
    }
    header {
      text-align: center;
      margin-bottom: 2rem;
    }
    h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.5rem; }
    p.subtitle { color: var(--text-muted); font-size: 0.9rem; }
    
    /* Progress Stepper */
    .stepper {
      display: flex;
      justify-content: space-between;
      margin-bottom: 2rem;
      position: relative;
    }
    .stepper::before {
      content: '';
      position: absolute;
      top: 15px;
      left: 30px;
      right: 30px;
      height: 2px;
      background: var(--border-color);
      z-index: 1;
    }
    .step-indicator {
      position: relative;
      z-index: 2;
      background: var(--bg-dark);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 0 0.5rem;
    }
    .step-circle {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: var(--card-bg);
      border: 2px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      transition: all 0.3s;
    }
    .step-indicator.active .step-circle {
      background: var(--primary);
      border-color: var(--primary);
      color: white;
    }
    .step-indicator.completed .step-circle {
      background: var(--success);
      border-color: var(--success);
      color: white;
    }
    .step-label {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }
    .step-indicator.active .step-label { color: var(--text-main); }
    
    /* Card Frame */
    .wizard-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5);
    }
    
    .step-view { display: none; }
    .step-view.active { display: block; }

    /* Tier Selector Cards */
    .tier-options {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin: 1.5rem 0;
    }
    .tier-card {
      border: 2px solid var(--border-color);
      border-radius: 8px;
      padding: 1.25rem;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: all 0.2s;
    }
    .tier-card:hover {
      border-color: #3b82f6aa;
      background: rgba(59, 130, 246, 0.05);
    }
    .tier-card.selected {
      border-color: var(--primary);
      background: rgba(59, 130, 246, 0.12);
    }
    .tier-title { font-weight: 600; font-size: 1rem; }
    .tier-price { font-weight: 700; color: #38bdf8; font-size: 1.1rem; }
    
    /* Forms */
    .form-group { margin-bottom: 1.25rem; }
    .form-group label {
      display: block;
      font-size: 0.85rem;
      margin-bottom: 0.4rem;
      color: var(--text-muted);
    }
    .form-group input, .form-group select {
      width: 100%;
      padding: 0.7rem 0.85rem;
      background: #090d16;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: white;
      font-size: 0.9rem;
    }
    .form-group input:focus, .form-group select:focus {
      outline: none;
      border-color: var(--primary);
    }
    .error-alert {
      background: #450a0a;
      border: 1px solid #7f1d1d;
      color: #fca5a5;
      padding: 0.6rem 1rem;
      border-radius: 6px;
      font-size: 0.85rem;
      margin-bottom: 1rem;
      display: none;
    }

    /* Actions */
    .wizard-actions {
      display: flex;
      justify-content: space-between;
      margin-top: 2rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--border-color);
    }
    button {
      cursor: pointer;
      font-family: inherit;
      border-radius: 6px;
      padding: 0.65rem 1.5rem;
      font-weight: 600;
      transition: all 0.2s;
    }
    .btn-next, .btn-submit {
      background: var(--primary);
      color: white;
      border: none;
    }
    .btn-next:hover, .btn-submit:hover { background: var(--primary-hover); }
    .btn-back {
      background: #1e293b;
      color: var(--text-muted);
      border: 1px solid var(--border-color);
    }
    .btn-back:hover { background: #334155; color: white; }

    /* Summary & Confirmation */
    .summary-box {
      background: #090d16;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1.25rem;
      margin: 1.5rem 0;
      font-size: 0.9rem;
      line-height: 1.6;
    }
    .confirmation-box {
      text-align: center;
      padding: 2rem 1rem;
    }
    .confirm-icon {
      font-size: 3rem;
      margin-bottom: 1rem;
      color: var(--success);
    }
    .ref-code {
      font-family: monospace;
      font-size: 1.8rem;
      font-weight: 800;
      color: #38bdf8;
      letter-spacing: 2px;
      margin: 1rem 0;
      background: #090d16;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      display: inline-block;
      border: 1px dashed var(--primary);
    }
  </style>
</head>
<body>
  <div class="wizard-container">
    <header>
      <h1 id="booking-app-title">QA Certification & Testing Dispatch</h1>
      <p class="subtitle">Multi-Step Verification Workflow Engine</p>
    </header>

    <div class="stepper">
      <div class="step-indicator active" id="ind-1">
        <div class="step-circle">1</div>
        <div class="step-label">Tier</div>
      </div>
      <div class="step-indicator" id="ind-2">
        <div class="step-circle">2</div>
        <div class="step-label">Schedule</div>
      </div>
      <div class="step-indicator" id="ind-3">
        <div class="step-circle">3</div>
        <div class="step-label">Review</div>
      </div>
      <div class="step-indicator" id="ind-4">
        <div class="step-circle">4</div>
        <div class="step-label">Confirm</div>
      </div>
    </div>

    <div class="wizard-card">
      <!-- Step 1: Tier Selection -->
      <div class="step-view active" id="step-1">
        <h2>1. Select Certification Service Tier</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">Choose the automated QA rigor level required for this test flight.</p>
        <div class="error-alert" id="step1-error">Please select a service tier before proceeding.</div>
        <div class="tier-options">
          <div class="tier-card" id="tier-standard" onclick="selectTier('standard')">
            <div>
              <div class="tier-title">Standard Calibration</div>
              <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.25rem;">Deterministic regression & DOM verification</div>
            </div>
            <div class="tier-price">$150.00</div>
          </div>
          <div class="tier-card" id="tier-priority" onclick="selectTier('priority')">
            <div>
              <div class="tier-title">Priority QA & Stress Certification</div>
              <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.25rem;">High-concurrency browser automation & network HAR audit</div>
            </div>
            <div class="tier-price">$350.00</div>
          </div>
          <div class="tier-card" id="tier-enterprise" onclick="selectTier('enterprise')">
            <div>
              <div class="tier-title">Enterprise Multi-Axis Inspection</div>
              <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 0.25rem;">Autonomous LLM agent exploration with remediation verification</div>
            </div>
            <div class="tier-price">$800.00</div>
          </div>
        </div>
        <div class="wizard-actions" style="justify-content: flex-end;">
          <button type="button" class="btn-next" id="btn-step1-next" onclick="goToStep2()">Next: Schedule Details &rarr;</button>
        </div>
      </div>

      <!-- Step 2: Schedule & Contact -->
      <div class="step-view" id="step-2">
        <h2>2. Schedule & Contact Details</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">Specify engineering contact and target test date.</p>
        <div class="error-alert" id="step2-error"></div>
        <div style="margin-top: 1.5rem;">
          <div class="form-group">
            <label for="input-customer-name">Engineering Lead Name *</label>
            <input type="text" id="input-customer-name" placeholder="e.g. Alice Engineering" />
          </div>
          <div class="form-group">
            <label for="input-customer-email">Corporate Email *</label>
            <input type="email" id="input-customer-email" placeholder="e.g. alice@eng-corp.internal" />
          </div>
          <div class="form-group">
            <label for="input-scheduled-date">Scheduled Execution Date *</label>
            <input type="date" id="input-scheduled-date" value="2026-10-15" />
          </div>
          <div class="form-group">
            <label for="select-facility">Testing Cluster Facility</label>
            <select id="select-facility">
              <option value="Main Lab - Boston">Main Lab - Boston</option>
              <option value="Aerospace Facility - Austin">Aerospace Facility - Austin</option>
              <option value="Testing Center - Berlin">Testing Center - Berlin</option>
            </select>
          </div>
        </div>
        <div class="wizard-actions">
          <button type="button" class="btn-back" id="btn-step2-back" onclick="goToStep(1)">&larr; Back</button>
          <button type="button" class="btn-next" id="btn-step2-next" onclick="goToStep3()">Next: Review &amp; Options &rarr;</button>
        </div>
      </div>

      <!-- Step 3: Review & Options -->
      <div class="step-view" id="step-3">
        <h2>3. Review &amp; Add-on Configuration</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">Confirm details and activate additional telemetry collection pipelines.</p>
        
        <div class="summary-box" id="booking-review-summary">
          <!-- Populated dynamically -->
        </div>

        <div style="margin: 1.5rem 0;">
          <div style="margin-bottom: 0.75rem;">
            <label style="cursor: pointer; display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem;">
              <input type="checkbox" id="checkbox-expedited-qa" onchange="updateSummary()" />
              <span>Expedited QA Execution Queue (+$75.00)</span>
            </label>
          </div>
          <div>
            <label style="cursor: pointer; display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem;">
              <input type="checkbox" id="checkbox-audit-log" onchange="updateSummary()" />
              <span>Cryptographic Proof &amp; Immutable Audit Log (+$50.00)</span>
            </label>
          </div>
        </div>

        <div style="text-align: right; font-size: 1.25rem; font-weight: 700; margin-bottom: 1.5rem;">
          Total Cost: <span id="booking-total-price" style="color: #38bdf8;">$350.00</span>
        </div>

        <div class="wizard-actions">
          <button type="button" class="btn-back" id="btn-step3-back" onclick="goToStep(2)">&larr; Back</button>
          <button type="button" class="btn-submit" id="btn-submit-booking" onclick="submitBooking()">Submit Booking Request</button>
        </div>
      </div>

      <!-- Step 4: Confirmation -->
      <div class="step-view" id="step-4">
        <div class="confirmation-box">
          <div class="confirm-icon">&#10004;</div>
          <h2 id="confirmation-badge" style="color: var(--success); font-size: 1.5rem; margin-bottom: 0.5rem;">Booking Confirmed!</h2>
          <p style="color: var(--text-muted); font-size: 0.9rem;">Your test certification workflow has been registered and scheduled.</p>
          <div class="ref-code" id="booking-reference-code">BK-PENDING</div>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem;">Status: <strong style="color: white;">CONFIRMED</strong> | Dispatch Queue: <strong>Active</strong></p>
          <div style="margin-top: 2rem;">
            <button type="button" class="btn-back" id="btn-new-booking" onclick="resetWizard()">Schedule Another Workflow</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentStep = 1;
    let selectedTier = null;
    const tierPrices = { standard: 150.0, priority: 350.0, enterprise: 800.0 };
    const tierNames = { standard: "Standard Calibration", priority: "Priority QA & Stress Certification", enterprise: "Enterprise Multi-Axis Inspection" };

    function selectTier(tier) {
      selectedTier = tier;
      document.querySelectorAll('.tier-card').forEach(el => el.classList.remove('selected'));
      const activeCard = document.getElementById(`tier-${tier}`);
      if (activeCard) activeCard.classList.add('selected');
      document.getElementById('step1-error').style.display = 'none';
    }

    function goToStep(s) {
      currentStep = s;
      document.querySelectorAll('.step-view').forEach(v => v.classList.remove('active'));
      document.getElementById(`step-${s}`).classList.add('active');

      // Update stepper indicators
      for (let i = 1; i <= 4; i++) {
        const ind = document.getElementById(`ind-${i}`);
        ind.classList.remove('active', 'completed');
        if (i < s) ind.classList.add('completed');
        else if (i === s) ind.classList.add('active');
      }
    }

    function goToStep2() {
      if (!selectedTier) {
        document.getElementById('step1-error').style.display = 'block';
        return;
      }
      goToStep(2);
    }

    function goToStep3() {
      const name = document.getElementById('input-customer-name').value.trim();
      const email = document.getElementById('input-customer-email').value.trim();
      const date = document.getElementById('input-scheduled-date').value.trim();
      const errBox = document.getElementById('step2-error');

      if (!name) {
        errBox.innerText = "Please enter engineering lead name.";
        errBox.style.display = 'block';
        return;
      }
      if (!email || !email.includes('@') || !email.includes('.')) {
        errBox.innerText = "Please enter a valid corporate email address.";
        errBox.style.display = 'block';
        return;
      }
      if (!date) {
        errBox.innerText = "Please select a scheduled execution date.";
        errBox.style.display = 'block';
        return;
      }

      errBox.style.display = 'none';
      updateSummary();
      goToStep(3);
    }

    function updateSummary() {
      const name = document.getElementById('input-customer-name').value.trim();
      const email = document.getElementById('input-customer-email').value.trim();
      const date = document.getElementById('input-scheduled-date').value.trim();
      const facility = document.getElementById('select-facility').value;
      const expedited = document.getElementById('checkbox-expedited-qa').checked;
      const audit = document.getElementById('checkbox-audit-log').checked;

      let total = tierPrices[selectedTier] || 150.0;
      if (expedited) total += 75.0;
      if (audit) total += 50.0;

      document.getElementById('booking-review-summary').innerHTML = `
        <strong>Service Tier:</strong> ${tierNames[selectedTier]} ($${tierPrices[selectedTier].toFixed(2)})<br/>
        <strong>Engineering Lead:</strong> ${name} &lt;${email}&gt;<br/>
        <strong>Target Date:</strong> ${date} (${facility})<br/>
        <strong>Add-ons:</strong> ${expedited ? 'Expedited (+ $75.00), ' : ''}${audit ? 'Audit Log (+ $50.00)' : (!expedited ? 'None' : '')}
      `;
      document.getElementById('booking-total-price').innerText = `$${total.toFixed(2)}`;
    }

    async function submitBooking() {
      const name = document.getElementById('input-customer-name').value.trim();
      const email = document.getElementById('input-customer-email').value.trim();
      const date = document.getElementById('input-scheduled-date').value.trim();
      const facility = document.getElementById('select-facility').value;
      const expedited = document.getElementById('checkbox-expedited-qa').checked;
      const audit = document.getElementById('checkbox-audit-log').checked;

      const payload = {
        service_tier: selectedTier,
        customer_name: name,
        customer_email: email,
        scheduled_date: date,
        facility: facility,
        expedited_qa: expedited,
        audit_log: audit
      };

      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        document.getElementById('booking-reference-code').innerText = data.reference_code;
        goToStep(4);
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to submit booking');
      }
    }

    function resetWizard() {
      selectedTier = null;
      document.querySelectorAll('.tier-card').forEach(el => el.classList.remove('selected'));
      document.getElementById('input-customer-name').value = '';
      document.getElementById('input-customer-email').value = '';
      document.getElementById('checkbox-expedited-qa').checked = false;
      document.getElementById('checkbox-audit-log').checked = false;
      goToStep(1);
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_TEMPLATE, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8090)
