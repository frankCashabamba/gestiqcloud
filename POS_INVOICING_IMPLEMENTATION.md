# POS → Invoicing/Sales/Expenses Implementation

## ✅ What Was Implemented

### Files Created

1. **`app/modules/pos/application/invoice_integration.py`**
   - `POSInvoicingService` class with methods to create Invoice, Sale, and Expense documents from POS receipts
   - Automatically checks if modules are enabled before creating documents
   - Handles all document linking and database transactions

2. **Modified: `app/modules/pos/interface/http/tenant.py`**
   - Updated `checkout()` endpoint to create complementary documents
   - Returns `documents_created` in response showing what was created

### How It Works

When a customer completes a POS checkout:

```
POST /api/v1/tenant/pos/receipts/{receipt_id}/checkout
└── checkout() endpoint:
    ├── 1. Validate receipt is in draft state
    ├── 2. Insert payments
    ├── 3. Calculate totals
    ├── 4. Determine warehouse
    ├── 5. Process stock for each line
    ├── 6. Mark receipt as paid
    └── 7. CREATE COMPLEMENTARY DOCUMENTS ✨
        ├── If invoicing enabled → Create Invoice
        ├── If sales enabled → Create Sale
        └── If expenses enabled + type="return" → Create Expense (refund)
```

### API Response Example

```json
{
  "ok": true,
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paid",
  "totals": {
    "subtotal": 100.00,
    "tax": 10.00,
    "total": 110.00,
    "paid": 110.00,
    "change": 0.00
  },
  "documents_created": {
    "invoice": {
      "invoice_id": "660e8400-e29b-41d4-a716-446655440000",
      "invoice_number": "A000001",
      "status": "draft",
      "subtotal": 100.00,
      "tax": 10.00,
      "total": 110.00
    },
    "sale": {
      "sale_id": "770e8400-e29b-41d4-a716-446655440000",
      "sale_type": "pos_sale",
      "status": "completed",
      "total": 110.00
    }
  }
}
```

---

## 🔧 Configuration per Module

### 1. Enable Invoicing Module

```bash
POST /api/v1/settings/modules/invoicing
Content-Type: application/json

{
  "enabled": true,
  "config": {
    "auto_create_on_checkout": true,
    "document_series": "A",
    "numbering_scheme": "yearly",
    "requires_customer": false
  }
}
```

**Effect**: Each POS checkout will auto-create a formal Invoice document that can be sent for electronic authorization (if einvoicing enabled).

---

### 2. Enable Sales Module

```bash
POST /api/v1/settings/modules/sales
Content-Type: application/json

{
  "enabled": true,
  "config": {
    "track_pos_sales": true,
    "customer_required": false,
    "auto_calculate_commission": false
  }
}
```

**Effect**: Each POS checkout will create a Sale record for tracking, reporting, and CRM purposes.

---

### 3. Enable Expenses Module (for Returns)

```bash
POST /api/v1/settings/modules/expenses
Content-Type: application/json

{
  "enabled": true,
  "config": {
    "track_refunds": true,
    "require_approval": false
  }
}
```

**Effect**: When processing a POS return (negative amount), an Expense/Refund record is created.

**Usage**: Only include if tenant wants to track returns/refunds as expenses.

---

## 🛠️ Usage Examples

### Basic Setup: POS Only (No Invoicing)

```bash
# Disable invoicing
POST /api/v1/settings/modules/invoicing
{ "enabled": false }

# Do POS checkout
POST /api/v1/tenant/pos/receipts/{receipt_id}/checkout
{
  "warehouse_id": "...",
  "payments": [{"method": "cash", "amount": 110.00}]
}

# Response: only receipt, no invoice created
{
  "ok": true,
  "receipt_id": "...",
  "documents_created": {}
}
```

---

### Professional Setup: Full ERP

```bash
# Enable all modules
POST /api/v1/settings/modules/invoicing { "enabled": true }
POST /api/v1/settings/modules/sales { "enabled": true }
POST /api/v1/settings/modules/einvoicing { "enabled": true }
POST /api/v1/settings/modules/expenses { "enabled": true }

# Do POS checkout
POST /api/v1/tenant/pos/receipts/{receipt_id}/checkout
{
  "warehouse_id": "...",
  "payments": [{"method": "card", "amount": 110.00}]
}

# Response: All documents created
{
  "ok": true,
  "receipt_id": "...",
  "documents_created": {
    "invoice": {...},      # For tax/invoicing
    "sale": {...},         # For CRM/sales tracking
    "expense": {...}       # If return
  }
}
```

---

### SaaS Plans Example

#### Plan A: Basic (Retail)
- ✅ POS (required)
- ✅ Inventory (required)
- ✅ Invoicing (required)
- ❌ Sales tracking
- ❌ Expenses
- ❌ E-invoicing

```python
enabled_modules = ["pos", "inventory", "invoicing"]
```

---

#### Plan B: Professional (Full ERP)
- ✅ POS
- ✅ Inventory
- ✅ Invoicing
- ✅ E-invoicing
- ✅ Sales
- ✅ Expenses
- ✅ Finance
- ✅ CRM

```python
enabled_modules = [
    "pos", "inventory", "invoicing", "einvoicing",
    "sales", "expenses", "finance", "crm"
]
```

---

## 📊 Database Impact

### Tables Involved

| Table | When | By |
|-------|------|-----|
| `pos_receipts` | Always | POS checkout |
| `invoices` | If invoicing enabled | `create_invoice_from_receipt()` |
| `invoice_lines` | If invoicing enabled | `create_invoice_from_receipt()` |
| `sales` | If sales enabled | `create_sale_from_receipt()` |
| `expenses` | If expenses enabled + return | `create_expense_from_receipt()` |

### Foreign Keys

```
pos_receipts
├── pos_receipt_id → invoices (optional)
├── pos_receipt_id → sales (optional)
└── pos_receipt_id → expenses (optional)
```

---

## 🧪 Testing

### Test Case 1: Invoicing Only

```python
def test_pos_checkout_creates_invoice():
    # Enable invoicing, disable sales/expenses
    tenant.enabled_modules = ["invoicing"]
    
    # Do checkout
    response = client.post(
        f"/api/v1/tenant/pos/receipts/{receipt_id}/checkout",
        json={"warehouse_id": "...", "payments": [...]}
    )
    
    # Verify
    assert response["documents_created"]["invoice"] is not None
    assert "sale" not in response["documents_created"]
    assert "expense" not in response["documents_created"]
```

### Test Case 2: Full Setup

```python
def test_pos_checkout_creates_all_documents():
    # Enable all modules
    tenant.enabled_modules = ["invoicing", "sales", "expenses"]
    
    # Do checkout
    response = client.post(...)
    
    # Verify
    assert response["documents_created"]["invoice"] is not None
    assert response["documents_created"]["sale"] is not None
    # expense not created unless type="return"
```

### Test Case 3: Return with Expenses

```python
def test_pos_return_creates_expense():
    # Enable expenses
    tenant.enabled_modules = ["expenses"]
    
    # Do checkout with type="return"
    response = client.post(
        f"/api/v1/tenant/pos/receipts/{receipt_id}/checkout",
        json={
            "type": "return",
            "warehouse_id": "...",
            "payments": [{"method": "refund", "amount": 110.00}]
        }
    )
    
    # Verify
    assert response["documents_created"]["expense"]["expense_type"] == "refund"
```

---

## 🚀 Frontend Integration

When calling POS checkout from frontend, check `documents_created` response:

```typescript
// Frontend: apps/tenant/src/modules/pos/api.ts

export async function checkoutReceipt(receiptId: string, payload: CheckoutPayload) {
  const response = await api.post(
    `/api/v1/tenant/pos/receipts/${receiptId}/checkout`,
    payload
  );
  
  const { documents_created, totals } = response;
  
  // Show toast with what was created
  const created = Object.keys(documents_created);
  if (created.length > 0) {
    showNotification({
      title: "Sale completed",
      message: `Invoice, Sale, and tracking documents created`,
      type: "success"
    });
  }
  
  return response;
}
```

---

## 🔍 Debugging

### Check Module Status

```python
# Backend: Check what modules are enabled
from app.modules.settings.infrastructure.repositories import SettingsRepo

repo = SettingsRepo(db)
settings = repo.get("enabled_modules")
print(f"Enabled modules: {settings}")

# Output: ["pos", "invoicing", "sales", "expenses"]
```

### Check if Document Was Created

```sql
-- Query to verify invoice was created from receipt
SELECT 
  r.id as receipt_id,
  r.invoice_id,
  i.invoice_number,
  i.status
FROM pos_receipts r
LEFT JOIN invoices i ON r.invoice_id = i.id
WHERE r.id = 'receipt-uuid';
```

---

## ⚠️ Important Notes

1. **Module Dependencies**: POS depends on `invoicing` and `inventory`. If user tries to enable POS without them, system auto-enables.

2. **No Data Loss**: If you disable invoicing after creating receipts, existing invoices remain. Only NEW checkouts won't create new invoices.

3. **Configuration is Per-Tenant**: Each tenant can have different modules enabled independently.

4. **Manual Override**: If auto-creation fails, admins can manually create Invoice/Sale/Expense from UI.

---

## 🎯 Next Steps

1. ✅ **Backend**: Implemented `POSInvoicingService`
2. ✅ **Backend**: Integrated with POS checkout endpoint
3. 📝 **Frontend**: Update POS checkout UI to show created documents
4. 📝 **Testing**: Add test cases for all module combinations
5. 📝 **Documentation**: Create admin guide for module configuration
6. 🚀 **Deployment**: Migrate database with any new tables (if needed)

---

## 📚 Related Documentation

- [Module System Architecture](./MODULAR_ARCHITECTURE_GUIDE.md)
- [POS Module Documentation](./apps/backend/app/modules/pos/README.md)
- [Settings Module](./apps/backend/app/modules/settings/README.md)
