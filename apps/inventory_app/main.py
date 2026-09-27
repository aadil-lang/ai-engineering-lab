import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Enterprise Asset & Inventory Management",
    description="Business CRUD application managing industrial parts, inventory levels, and asset allocations.",
    version="1.0.0",
)

class InventoryItem(BaseModel):
    sku: str
    name: str
    category: str
    quantity: int = Field(ge=0, description="Quantity must be non-negative")
    unit_price: float = Field(ge=0.0, description="Unit price must be non-negative")
    status: str = "IN_STOCK"

class InventoryItemCreate(BaseModel):
    sku: str
    name: str
    category: str
    quantity: int
    unit_price: float

class InventoryItemUpdate(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    category: Optional[str] = None
    name: Optional[str] = None

# In-memory store initialized with baseline records
INVENTORY_DB: dict[str, dict] = {
    "SKU-1001": {
        "sku": "SKU-1001",
        "name": "Titanium Hex Bolt M8",
        "category": "Fasteners",
        "quantity": 120,
        "unit_price": 4.50,
        "status": "IN_STOCK",
    },
    "SKU-1002": {
        "sku": "SKU-1002",
        "name": "Steel Ball Bearing 608RS",
        "category": "Bearings",
        "quantity": 45,
        "unit_price": 12.80,
        "status": "IN_STOCK",
    },
    "SKU-1003": {
        "sku": "SKU-1003",
        "name": "Pneumatic Solenoid Valve",
        "category": "Pneumatics",
        "quantity": 8,
        "unit_price": 85.00,
        "status": "LOW_STOCK",
    },
    "SKU-1004": {
        "sku": "SKU-1004",
        "name": "Linear Optical Shaft 12mm",
        "category": "Linear Motion",
        "quantity": 22,
        "unit_price": 34.20,
        "status": "IN_STOCK",
    },
    "SKU-1005": {
        "sku": "SKU-1005",
        "name": "Flexible Shaft Coupler",
        "category": "Couplings",
        "quantity": 60,
        "unit_price": 15.75,
        "status": "IN_STOCK",
    },
}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Enterprise Asset & Inventory Management",
        "version": "1.0.0",
        "total_items": len(INVENTORY_DB),
    }

@app.get("/api/inventory")
def list_inventory():
    return list(INVENTORY_DB.values())

@app.get("/api/inventory/{sku}")
def get_inventory_item(sku: str):
    if sku not in INVENTORY_DB:
        raise HTTPException(status_code=404, detail=f"Inventory item '{sku}' not found")
    return INVENTORY_DB[sku]

@app.post("/api/inventory", status_code=status.HTTP_201_CREATED)
def create_inventory_item(item: InventoryItemCreate):
    sku = item.sku.strip()
    name = item.name.strip()
    if not sku:
        raise HTTPException(status_code=422, detail="SKU cannot be empty")
    if not name:
        raise HTTPException(status_code=422, detail="Item name cannot be empty")
    if item.quantity < 0:
        raise HTTPException(status_code=422, detail="Quantity cannot be negative")
    if item.unit_price < 0:
        raise HTTPException(status_code=422, detail="Unit price cannot be negative")
    if sku in INVENTORY_DB:
        raise HTTPException(status_code=409, detail=f"Item with SKU '{sku}' already exists")

    new_item = {
        "sku": sku,
        "name": name,
        "category": item.category.strip() or "General",
        "quantity": item.quantity,
        "unit_price": float(item.unit_price),
        "status": "LOW_STOCK" if item.quantity < 10 else "IN_STOCK",
    }
    INVENTORY_DB[sku] = new_item
    return new_item

@app.put("/api/inventory/{sku}")
def update_inventory_item(sku: str, payload: InventoryItemUpdate):
    if sku not in INVENTORY_DB:
        raise HTTPException(status_code=404, detail=f"Item '{sku}' not found")
    item = INVENTORY_DB[sku]
    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status_code=422, detail="Item name cannot be empty")
        item["name"] = payload.name.strip()
    if payload.category is not None:
        item["category"] = payload.category.strip()
    if payload.quantity is not None:
        if payload.quantity < 0:
            raise HTTPException(status_code=422, detail="Quantity cannot be negative")
        item["quantity"] = payload.quantity
        item["status"] = "OUT_OF_STOCK" if item["quantity"] == 0 else ("LOW_STOCK" if item["quantity"] < 10 else "IN_STOCK")
    if payload.unit_price is not None:
        if payload.unit_price < 0:
            raise HTTPException(status_code=422, detail="Unit price cannot be negative")
        item["unit_price"] = float(payload.unit_price)
    return item

@app.delete("/api/inventory/{sku}")
def delete_inventory_item(sku: str):
    if sku not in INVENTORY_DB:
        raise HTTPException(status_code=404, detail=f"Item '{sku}' not found")
    deleted = INVENTORY_DB.pop(sku)
    return {"message": "Deleted successfully", "item": deleted}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Enterprise Asset & Inventory Management</title>
  <style>
    :root {
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --border-color: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 2rem;
      min-height: 100vh;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 1rem;
    }
    h1 { font-size: 1.5rem; font-weight: 700; color: var(--text-main); }
    .badge {
      padding: 0.25rem 0.6rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .badge-success { background: #064e3b; color: #34d399; }
    .badge-warning { background: #78350f; color: #fbbf24; }
    .badge-danger { background: #7f1d1d; color: #f87171; }
    
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .stat-card {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem 1.5rem;
    }
    .stat-card .label { font-size: 0.85rem; color: var(--text-muted); }
    .stat-card .val { font-size: 1.5rem; font-weight: bold; margin-top: 0.25rem; }
    
    .table-container {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
    }
    .table-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.5rem;
      border-bottom: 1px solid var(--border-color);
    }
    table { width: 100%; border-collapse: collapse; text-align: left; }
    th {
      background: #0f172a;
      padding: 0.75rem 1.5rem;
      font-size: 0.8rem;
      text-transform: uppercase;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-color);
    }
    td {
      padding: 0.85rem 1.5rem;
      border-bottom: 1px solid var(--border-color);
      font-size: 0.9rem;
    }
    tr:hover { background: rgba(255,255,255,0.02); }
    
    button {
      cursor: pointer;
      font-family: inherit;
      border-radius: 6px;
      transition: all 0.2s;
    }
    .btn-primary {
      background: var(--primary);
      color: #0f172a;
      border: none;
      padding: 0.6rem 1.2rem;
      font-weight: 600;
    }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-secondary {
      background: #334155;
      color: var(--text-main);
      border: none;
      padding: 0.4rem 0.8rem;
      font-size: 0.8rem;
    }
    .btn-secondary:hover { background: #475569; }

    /* Modal */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    .modal {
      background: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      width: 480px;
      padding: 1.5rem;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .modal h2 { margin-bottom: 1rem; font-size: 1.25rem; }
    .form-group { margin-bottom: 1rem; }
    .form-group label {
      display: block;
      font-size: 0.85rem;
      margin-bottom: 0.35rem;
      color: var(--text-muted);
    }
    .form-group input {
      width: 100%;
      padding: 0.6rem;
      background: #0f172a;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: white;
      font-size: 0.9rem;
    }
    .error-msg {
      color: var(--danger);
      font-size: 0.75rem;
      margin-top: 0.25rem;
      display: none;
    }
    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.5rem;
      margin-top: 1.5rem;
    }
    
    /* Toast */
    #toast-notification {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: #064e3b;
      color: #34d399;
      border: 1px solid #059669;
      padding: 0.75rem 1.5rem;
      border-radius: 6px;
      display: none;
      font-weight: 500;
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1 id="app-title">Industrial Inventory & Asset Management</h1>
      <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">Live CRUD Workflow & Asset Status Operations</p>
    </div>
    <div>
      <span class="badge badge-success" id="service-status">ONLINE (Port 8089)</span>
    </div>
  </header>

  <div class="stats-bar">
    <div class="stat-card">
      <div class="label">Total Managed SKUs</div>
      <div class="val" id="stat-total-skus">5</div>
    </div>
    <div class="stat-card">
      <div class="label">Low Stock Alerts</div>
      <div class="val" id="stat-low-stock" style="color: var(--warning);">1</div>
    </div>
    <div class="stat-card">
      <div class="label">Total Stock Quantity</div>
      <div class="val" id="stat-total-quantity">255</div>
    </div>
  </div>

  <div class="table-container">
    <div class="table-header-row">
      <h2 style="font-size: 1.1rem;">Inventory Catalogue</h2>
      <div style="display: flex; gap: 1rem; align-items: center;">
        <input type="text" id="search-input" placeholder="Search catalogue..." oninput="filterInventory(this.value)" style="padding: 0.45rem 0.85rem; border-radius: 6px; border: 1px solid var(--border-color); background: #090d16; color: white; font-size: 0.85rem;" />
        <button class="btn-primary" id="btn-add-item" onclick="openAddModal()">+ Add New Item</button>
      </div>
    </div>
    <table id="inventory-table">
      <thead>
        <tr>
          <th>SKU</th>
          <th>Name</th>
          <th>Category</th>
          <th>Stock Quantity</th>
          <th>Unit Price</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="inventory-tbody">
        <!-- Rendered via JS -->
      </tbody>
    </table>
  </div>

  <!-- Add Item Modal -->
  <div class="modal-overlay" id="modal-add-item">
    <div class="modal">
      <h2>Add Inventory Item</h2>
      <form id="form-add-item" onsubmit="event.preventDefault(); submitAddItem();">
        <div class="form-group">
          <label for="input-sku">Part SKU *</label>
          <input type="text" id="input-sku" placeholder="e.g. SKU-9921" />
          <div class="error-msg" id="sku-error">SKU is required and must be unique.</div>
        </div>
        <div class="form-group">
          <label for="input-name">Item Name *</label>
          <input type="text" id="input-name" placeholder="e.g. Hydraulic Actuator" />
          <div class="error-msg" id="name-error">Item name is required.</div>
        </div>
        <div class="form-group">
          <label for="input-category">Category</label>
          <input type="text" id="input-category" placeholder="e.g. Mechanical" value="Mechanical" />
        </div>
        <div class="form-group">
          <label for="input-quantity">Initial Stock Quantity *</label>
          <input type="number" id="input-quantity" value="10" />
          <div class="error-msg" id="quantity-error">Quantity cannot be negative.</div>
        </div>
        <div class="form-group">
          <label for="input-price">Unit Price ($) *</label>
          <input type="number" step="0.01" id="input-price" value="25.00" />
          <div class="error-msg" id="price-error">Price cannot be negative.</div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary" id="btn-cancel-item" onclick="closeAddModal()">Cancel</button>
          <button type="submit" class="btn-primary" id="btn-submit-item">Create Item</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Edit Item Modal -->
  <div class="modal-overlay" id="modal-edit-item">
    <div class="modal">
      <h2>Edit Item Stock</h2>
      <form id="form-edit-item" onsubmit="event.preventDefault(); submitEditItem();">
        <input type="hidden" id="edit-sku" />
        <div class="form-group">
          <label>Item Name</label>
          <div id="edit-item-name" style="font-weight: 600; margin-bottom: 0.5rem;"></div>
        </div>
        <div class="form-group">
          <label for="input-edit-quantity">Updated Stock Quantity *</label>
          <input type="number" id="input-edit-quantity" />
          <div class="error-msg" id="edit-quantity-error">Quantity cannot be negative.</div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn-secondary" onclick="closeEditModal()">Cancel</button>
          <button type="submit" class="btn-primary" id="btn-save-edit">Save Changes</button>
        </div>
      </form>
    </div>
  </div>

  <div id="toast-notification">Operation completed successfully</div>

  <script>
    async function fetchInventory() {
      const res = await fetch('/api/inventory');
      const data = await res.json();
      renderTable(data);
      updateStats(data);
    }

    function renderTable(items) {
      const tbody = document.getElementById('inventory-tbody');
      tbody.innerHTML = '';
      items.forEach(item => {
        const tr = document.createElement('tr');
        tr.id = `row-${item.sku}`;
        const badgeClass = item.status === 'IN_STOCK' ? 'badge-success' : (item.status === 'LOW_STOCK' ? 'badge-warning' : 'badge-danger');
        tr.innerHTML = `
          <td style="font-family: monospace; font-weight: 600;">${item.sku}</td>
          <td class="col-name">${item.name}</td>
          <td>${item.category}</td>
          <td class="col-quantity" id="qty-${item.sku}">${item.quantity}</td>
          <td>$${parseFloat(item.unit_price).toFixed(2)}</td>
          <td><span class="badge ${badgeClass}">${item.status}</span></td>
          <td>
            <button class="btn-secondary" id="btn-edit-item-${item.sku}" onclick="openEditModal('${item.sku}', '${item.name.replace(/'/g, "\\\\'")}', ${item.quantity})">Edit</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    function updateStats(items) {
      document.getElementById('stat-total-skus').innerText = items.length;
      const lowStock = items.filter(i => i.status === 'LOW_STOCK' || i.quantity < 10).length;
      document.getElementById('stat-low-stock').innerText = lowStock;
      const totalQty = items.reduce((acc, cur) => acc + cur.quantity, 0);
      document.getElementById('stat-total-quantity').innerText = totalQty;
    }

    function showToast(msg) {
      const t = document.getElementById('toast-notification');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3000);
    }

    function openAddModal() {
      document.getElementById('input-sku').value = '';
      document.getElementById('input-name').value = '';
      document.getElementById('input-quantity').value = '10';
      document.getElementById('input-price').value = '25.00';
      hideErrors();
      document.getElementById('modal-add-item').style.display = 'flex';
    }

    function closeAddModal() {
      document.getElementById('modal-add-item').style.display = 'none';
      hideErrors();
    }

    function hideErrors() {
      document.getElementById('sku-error').style.display = 'none';
      document.getElementById('name-error').style.display = 'none';
      document.getElementById('quantity-error').style.display = 'none';
      document.getElementById('price-error').style.display = 'none';
    }

    async function submitAddItem() {
      hideErrors();
      const sku = document.getElementById('input-sku').value.trim();
      const name = document.getElementById('input-name').value.trim();
      const category = document.getElementById('input-category').value.trim() || 'General';
      const quantity = parseInt(document.getElementById('input-quantity').value, 10);
      const price = parseFloat(document.getElementById('input-price').value);

      let hasError = false;
      if (!sku) {
        document.getElementById('sku-error').style.display = 'block';
        hasError = true;
      }
      if (!name) {
        document.getElementById('name-error').style.display = 'block';
        hasError = true;
      }
      if (isNaN(quantity) || quantity < 0) {
        document.getElementById('quantity-error').style.display = 'block';
        hasError = true;
      }
      if (isNaN(price) || price < 0) {
        document.getElementById('price-error').style.display = 'block';
        hasError = true;
      }

      if (hasError) return;

      const res = await fetch('/api/inventory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku, name, category, quantity, unit_price: price })
      });

      if (res.ok) {
        closeAddModal();
        showToast(`Item ${name} (${sku}) created successfully!`);
        fetchInventory();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to create item');
      }
    }

    function openEditModal(sku, name, qty) {
      document.getElementById('edit-sku').value = sku;
      document.getElementById('edit-item-name').innerText = name + ' (' + sku + ')';
      document.getElementById('input-edit-quantity').value = qty;
      document.getElementById('edit-quantity-error').style.display = 'none';
      document.getElementById('modal-edit-item').style.display = 'flex';
    }

    function closeEditModal() {
      document.getElementById('modal-edit-item').style.display = 'none';
    }

    async function submitEditItem() {
      const sku = document.getElementById('edit-sku').value;
      const qty = parseInt(document.getElementById('input-edit-quantity').value, 10);
      if (isNaN(qty) || qty < 0) {
        document.getElementById('edit-quantity-error').style.display = 'block';
        return;
      }
      const res = await fetch(`/api/inventory/${sku}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: qty })
      });
      if (res.ok) {
        closeEditModal();
        showToast(`Item ${sku} updated to quantity ${qty}!`);
        fetchInventory();
      } else {
        alert('Failed to update item');
      }
    }

    function filterInventory(term) {
      const q = (term || '').toLowerCase();
      document.querySelectorAll('#inventory-tbody tr').forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    }

    window.addEventListener('DOMContentLoaded', fetchInventory);
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_TEMPLATE, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8089)
