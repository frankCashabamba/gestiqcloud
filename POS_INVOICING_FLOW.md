# POS to Invoicing/Sales/Expenses Flow - Architecture

## ✅ What You Already Have

### 1. **Module System** 
Already exists in `app/models/core/modulo.py`:
- `Module` - Catálogo de módulos disponibles
- `CompanyModule` - Módulos contratados por tenant
- `AssignedModule` - Módulos asignados a usuarios

### 2. **Module Catalog** 
`app/modules/settings/application/modules_catalog.py`:
```python
AVAILABLE_MODULES = [
    {"id": "pos", "dependencies": ["inventory", "invoicing"]},
    {"id": "invoicing", "required": True},
    {"id": "sales", "dependencies": ["inventory", "invoicing"]},
    {"id": "expenses", "dependencies": []},
    # ... más módulos
]
```

### 3. **Settings Service**
`app/modules/settings/application/use_cases.py`:
- `enable_module()` - Activa módulo respetando dependencias
- `disable_module()` - Desactiva módulo 
- `get_module_settings()` - Obtiene configuración del módulo

### 4. **POS Module**
`app/modules/pos/interface/http/tenant.py`:
- Crea recibos en tabla `pos_receipts`
- Las líneas se guardan en `pos_receipt_lines`

---

## 🎯 Implementation Strategy for POS → Invoicing/Sales/Expenses

### Step 1: Check Module Enabled Status
```python
# In POS checkout/finalize endpoint
from app.modules.settings.application.use_cases import SettingsManager

manager = SettingsManager(db)

# Verify required modules
if not manager.is_module_enabled(tenant_id, "invoicing"):
    raise HTTPException(400, "Invoicing module not enabled")

# Optional modules
should_create_sales_doc = manager.is_module_enabled(tenant_id, "sales")
should_create_expense = manager.is_module_enabled(tenant_id, "expenses")  # only for returns
```

### Step 2: Receipt → Invoice Bridge
After POS checkout, create invoice (if invoicing enabled):

```python
# File: apps/backend/app/modules/pos/interface/http/tenant.py (existing checkout)

@router.post("/receipts/{receipt_id}/checkout")
def checkout(receipt_id: str, payload: CheckoutIn, request: Request, db: Session):
    # ... existing POS checkout logic ...
    
    # ✅ NEW: Create invoice if invoicing enabled
    tenant_id = _get_tenant_id(request)
    manager = SettingsManager(db)
    
    if manager.is_module_enabled(tenant_id, "invoicing"):
        invoice = _create_invoice_from_receipt(
            db, 
            receipt_id, 
            tenant_id,
            payload.invoice_config  # tipo: "regular", "credit_note"
        )
        
        # If einvoicing enabled, queue for electronic submission
        if manager.is_module_enabled(tenant_id, "einvoicing"):
            queue_for_einvoicing(db, invoice.id)
```

### Step 3: Receipt → Sales Document
If sales module enabled, create sales order/tracking:

```python
if manager.is_module_enabled(tenant_id, "sales"):
    sale = _create_sale_from_receipt(
        db,
        receipt_id,
        customer_id=payload.customer_id,
        sale_type="pos_sale"  # para distinguir de órdenes manuales
    )
```

### Step 4: Receipt → Expense (Returns Only)
Only for devolutions/refunds:

```python
if payload.type == "return" and manager.is_module_enabled(tenant_id, "expenses"):
    expense = _create_expense_from_receipt(
        db,
        receipt_id,
        expense_type="refund",
        amount=payload.refund_amount
    )
```

---

## 📊 Data Flow Diagram

```
POS Receipt Created (pos_receipts)
    ↓
    Checkout Called
    ↓
    ├─→ Module Check: invoicing enabled?
    │   ├─ YES → Create Invoice (invoices table)
    │   │        ├─ Check: einvoicing enabled?
    │   │        │  └─ YES → Queue for electronic submission
    │   │        └─ Link: receipt.invoice_id = invoice.id
    │   └─ NO → Continue without invoice
    │
    ├─→ Module Check: sales enabled?
    │   ├─ YES → Create Sale (sales table)
    │   │        └─ Link: sale.receipt_id = receipt.id
    │   └─ NO → Skip sales tracking
    │
    └─→ Module Check: expenses enabled? + type = "return"?
        ├─ YES → Create Expense (expenses table)
        │        └─ Link: expense.receipt_id = receipt.id
        └─ NO → Skip expense tracking
```

---

## 📝 Configuration per Tenant

Each tenant can configure modules via:

```bash
# Enable invoicing module
POST /api/v1/settings/modules/invoicing
{
    "enabled": true,
    "config": {
        "auto_create_on_checkout": true,
        "document_series": "A",
        "numbering_scheme": "yearly"
    }
}

# Enable sales tracking
POST /api/v1/settings/modules/sales
{
    "enabled": true,
    "config": {
        "track_pos_sales": true,
        "customer_required": false
    }
}

# Enable expenses (optional)
POST /api/v1/settings/modules/expenses
{
    "enabled": true,
    "config": {
        "track_refunds": true
    }
}
```

---

## 🔧 Implementation Checklist

- [ ] **Step 1**: Add module check in POS checkout endpoint
- [ ] **Step 2**: Create `_create_invoice_from_receipt()` function
- [ ] **Step 3**: Create `_create_sale_from_receipt()` function (if needed)
- [ ] **Step 4**: Create `_create_expense_from_receipt()` for returns only
- [ ] **Step 5**: Queue invoices for electronic submission if einvoicing enabled
- [ ] **Step 6**: Create endpoint to view/edit POS→Invoice/Sale/Expense mappings
- [ ] **Step 7**: Add configuration UI for module settings

---

## 🎓 Key Points

1. **Module Dependencies**: 
   - POS depends on: `inventory` + `invoicing`
   - If user tries to enable POS without invoicing, system auto-enables it

2. **Configuration is per-Tenant**:
   - Each tenant can enable/disable modules independently
   - Settings stored in `company_settings` JSONB column

3. **Flexible Flow**:
   - Minimal setup: POS → Invoice only
   - Full setup: POS → Invoice → E-invoicing + Sales + Expenses
   - Tenant controls complexity

4. **Backward Compatible**:
   - If module disabled, code simply skips that step
   - No errors, just reduced features

---

## 📁 Files to Modify

1. **POS Checkout** → Add module checks
   - File: `app/modules/pos/interface/http/tenant.py`
   - Method: `checkout()` (line ~1644)

2. **Invoice Creation Functions** → New file
   - File: `app/modules/pos/application/invoice_service.py` (NEW)
   - Functions: `_create_invoice_from_receipt()`, etc.

3. **Settings Routes** → Already exists
   - File: `app/modules/settings/interface/http/settings_router.py`
   - No changes needed - just document

4. **Migrations** → If adding new tables
   - Alembic: No migrations needed, using existing tables

---

## Next Steps

Which would you like to implement first?

1. **Integration**: Modify POS checkout to create invoices based on module status
2. **UI**: Create configuration panel for module settings
3. **API**: Create endpoint to manage receipts → invoices → sales mappings
4. **Reporting**: Create dashboard showing POS revenue, invoicing status, etc.
