# API Examples & Testing Guide

## 🔌 API Examples

### 1. Enable/Disable Modules

#### Enable Invoicing
```bash
curl -X POST "http://localhost:8000/api/v1/settings/modules/invoicing" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "config": {
      "auto_create_on_checkout": true,
      "document_series": "A",
      "numbering_scheme": "yearly"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "module": "invoicing",
  "module_name": "Invoicing",
  "enabled": true,
  "updated_at": "2026-01-21T10:30:00Z"
}
```

#### Enable Sales
```bash
curl -X POST "http://localhost:8000/api/v1/settings/modules/sales" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "config": {
      "track_pos_sales": true,
      "customer_required": false
    }
  }'
```

#### Enable Expenses (for Returns/Refunds)
```bash
curl -X POST "http://localhost:8000/api/v1/settings/modules/expenses" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "config": {
      "track_refunds": true,
      "require_approval": false
    }
  }'
```

---

### 2. POS Checkout with Document Creation

#### Simple Checkout (All Modules Enabled)
```bash
curl -X POST "http://localhost:8000/api/v1/tenant/pos/receipts/550e8400-e29b-41d4-a716-446655440000/checkout" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "warehouse_id": "660e8400-e29b-41d4-a716-446655440001",
    "payments": [
      {
        "method": "cash",
        "amount": 110.00,
        "ref": null
      }
    ]
  }'
```

**Response (With All Documents Created):**
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
      "invoice_id": "770e8400-e29b-41d4-a716-446655440002",
      "invoice_number": "A000001",
      "status": "draft",
      "subtotal": 100.00,
      "tax": 10.00,
      "total": 110.00
    },
    "sale": {
      "sale_id": "880e8400-e29b-41d4-a716-446655440003",
      "sale_type": "pos_sale",
      "status": "completed",
      "total": 110.00
    }
  }
}
```

#### Checkout with Only Invoicing
```bash
# Same request, but with invoicing enabled and sales/expenses disabled
# Response will only have invoice in documents_created

{
  "ok": true,
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paid",
  "totals": { ... },
  "documents_created": {
    "invoice": {
      "invoice_id": "770e8400-e29b-41d4-a716-446655440002",
      "invoice_number": "A000001",
      "status": "draft",
      "subtotal": 100.00,
      "tax": 10.00,
      "total": 110.00
    }
  }
}
```

#### Checkout with No Modules
```bash
# All modules disabled
# Response will have empty documents_created

{
  "ok": true,
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paid",
  "totals": { ... },
  "documents_created": {}
}
```

#### Return/Refund with Expense Creation
```bash
curl -X POST "http://localhost:8000/api/v1/tenant/pos/receipts/550e8400-e29b-41d4-a716-446655440000/checkout" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "return",
    "warehouse_id": "660e8400-e29b-41d4-a716-446655440001",
    "payments": [
      {
        "method": "refund",
        "amount": 55.00,
        "ref": "Refund for damaged item"
      }
    ]
  }'
```

**Response (With Expense Created):**
```json
{
  "ok": true,
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "paid",
  "totals": {
    "subtotal": -50.00,
    "tax": -5.00,
    "total": -55.00,
    "paid": -55.00,
    "change": 0.00
  },
  "documents_created": {
    "expense": {
      "expense_id": "990e8400-e29b-41d4-a716-446655440004",
      "expense_type": "refund",
      "amount": 55.00,
      "status": "draft"
    }
  }
}
```

---

### 3. Verify Created Documents in Database

#### Check Created Invoice
```bash
curl -X GET "http://localhost:8000/api/v1/tenant/invoices/A000001" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### List All POS-Created Invoices
```bash
curl -X GET "http://localhost:8000/api/v1/tenant/invoices?source=pos" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Check Sales Records
```bash
curl -X GET "http://localhost:8000/api/v1/tenant/sales?type=pos_sale" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🧪 Testing Examples

### Python Test Example

```python
import pytest
import requests
from decimal import Decimal

BASE_URL = "http://localhost:8000"
TENANT_TOKEN = "your-auth-token"

def get_headers():
    return {
        "Authorization": f"Bearer {TENANT_TOKEN}",
        "Content-Type": "application/json"
    }

class TestPOSInvoicingIntegration:
    
    def test_checkout_with_invoicing_only(self):
        """Test that checkout creates invoice when invoicing enabled"""
        # Enable invoicing
        resp = requests.post(
            f"{BASE_URL}/api/v1/settings/modules/invoicing",
            json={"enabled": True},
            headers=get_headers()
        )
        assert resp.status_code == 200
        
        # Create receipt
        receipt = create_test_receipt()
        
        # Checkout
        checkout_resp = requests.post(
            f"{BASE_URL}/api/v1/tenant/pos/receipts/{receipt['id']}/checkout",
            json={
                "warehouse_id": "test-warehouse-id",
                "payments": [{"method": "cash", "amount": 110.00}]
            },
            headers=get_headers()
        )
        
        # Verify response
        assert checkout_resp.status_code == 200
        data = checkout_resp.json()
        assert data["ok"] == True
        assert "documents_created" in data
        assert "invoice" in data["documents_created"]
        
        invoice = data["documents_created"]["invoice"]
        assert invoice["status"] == "draft"
        assert invoice["total"] == 110.00
        assert invoice["invoice_number"].startswith("A")

    def test_checkout_with_all_modules(self):
        """Test that checkout creates all documents when all modules enabled"""
        # Enable all modules
        for module in ["invoicing", "sales", "expenses"]:
            requests.post(
                f"{BASE_URL}/api/v1/settings/modules/{module}",
                json={"enabled": True},
                headers=get_headers()
            )
        
        receipt = create_test_receipt()
        
        checkout_resp = requests.post(
            f"{BASE_URL}/api/v1/tenant/pos/receipts/{receipt['id']}/checkout",
            json={
                "warehouse_id": "test-warehouse-id",
                "payments": [{"method": "cash", "amount": 110.00}]
            },
            headers=get_headers()
        )
        
        data = checkout_resp.json()
        assert "invoice" in data["documents_created"]
        assert "sale" in data["documents_created"]
        # expense only if type="return"

    def test_checkout_with_no_modules(self):
        """Test that checkout works with no optional modules"""
        # Disable modules
        for module in ["invoicing", "sales", "expenses"]:
            requests.post(
                f"{BASE_URL}/api/v1/settings/modules/{module}",
                json={"enabled": False},
                headers=get_headers()
            )
        
        receipt = create_test_receipt()
        
        checkout_resp = requests.post(
            f"{BASE_URL}/api/v1/tenant/pos/receipts/{receipt['id']}/checkout",
            json={
                "warehouse_id": "test-warehouse-id",
                "payments": [{"method": "cash", "amount": 110.00}]
            },
            headers=get_headers()
        )
        
        data = checkout_resp.json()
        # Should still work, but no documents created
        assert data["ok"] == True
        assert data["documents_created"] == {}

    def test_return_creates_expense(self):
        """Test that refunds create expense records"""
        # Enable expenses
        requests.post(
            f"{BASE_URL}/api/v1/settings/modules/expenses",
            json={"enabled": True},
            headers=get_headers()
        )
        
        receipt = create_test_receipt(amount=-55.00)  # Negative for return
        
        checkout_resp = requests.post(
            f"{BASE_URL}/api/v1/tenant/pos/receipts/{receipt['id']}/checkout",
            json={
                "type": "return",
                "warehouse_id": "test-warehouse-id",
                "payments": [{"method": "refund", "amount": 55.00}]
            },
            headers=get_headers()
        )
        
        data = checkout_resp.json()
        assert "expense" in data["documents_created"]
        assert data["documents_created"]["expense"]["expense_type"] == "refund"

def create_test_receipt(amount: float = 110.00):
    """Helper to create a test receipt"""
    # Implementation depends on your test setup
    pass
```

### JavaScript/TypeScript Test Example

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { payReceipt, type CheckoutResponse } from '@/modules/pos/services'

describe('POS Invoicing Integration', () => {
  let receiptId: string
  
  beforeEach(() => {
    receiptId = 'test-receipt-id'
  })

  it('should create invoice when invoicing module enabled', async () => {
    const response = await payReceipt(receiptId, [
      { method: 'cash', amount: 110.00 }
    ])
    
    expect(response.ok).toBe(true)
    expect(response.documents_created).toBeDefined()
    expect(response.documents_created?.invoice).toBeDefined()
    expect(response.documents_created?.invoice?.invoice_number).toMatch(/^A\d+/)
  })

  it('should handle multiple payment methods', async () => {
    const response = await payReceipt(receiptId, [
      { method: 'cash', amount: 50.00 },
      { method: 'card', amount: 60.00 }
    ])
    
    expect(response.ok).toBe(true)
    expect(response.totals.paid).toBe(110.00)
  })

  it('should show all documents in CheckoutSummary', async () => {
    const response: CheckoutResponse = {
      ok: true,
      receipt_id: receiptId,
      status: 'paid',
      totals: {
        subtotal: 100.00,
        tax: 10.00,
        total: 110.00,
        paid: 110.00,
        change: 0.00
      },
      documents_created: {
        invoice: {
          invoice_id: 'inv-1',
          invoice_number: 'A000001',
          status: 'draft',
          subtotal: 100.00,
          tax: 10.00,
          total: 110.00
        },
        sale: {
          sale_id: 'sale-1',
          sale_type: 'pos_sale',
          status: 'completed',
          total: 110.00
        }
      }
    }
    
    // Mount component
    const { getByText } = render(
      <CheckoutSummary response={response} />
    )
    
    expect(getByText('Factura Electrónica')).toBeInTheDocument()
    expect(getByText('Venta Registrada')).toBeInTheDocument()
    expect(getByText('A000001')).toBeInTheDocument()
  })
})
```

---

## 📊 SQL Testing Queries

### Verify Document Creation
```sql
-- Check invoices created from POS
SELECT 
  p.id as receipt_id,
  p.gross_total as receipt_total,
  i.id as invoice_id,
  i.invoice_number,
  i.total_amount as invoice_total,
  i.status
FROM pos_receipts p
LEFT JOIN invoices i ON p.invoice_id = i.id
WHERE p.status = 'paid'
ORDER BY p.created_at DESC
LIMIT 10;
```

### Check Sales Created
```sql
-- Check sales created from POS
SELECT 
  p.id as receipt_id,
  s.id as sale_id,
  s.sale_type,
  s.status,
  s.total_amount,
  s.created_at
FROM pos_receipts p
LEFT JOIN sales s ON s.pos_receipt_id = p.id
WHERE s.sale_type = 'pos_sale'
ORDER BY p.created_at DESC
LIMIT 10;
```

### Check Expenses Created
```sql
-- Check expenses created from POS (refunds)
SELECT 
  p.id as receipt_id,
  e.id as expense_id,
  e.expense_type,
  e.amount,
  e.status,
  e.created_at
FROM pos_receipts p
LEFT JOIN expenses e ON e.pos_receipt_id = p.id
WHERE e.expense_type IN ('refund', 'return')
ORDER BY p.created_at DESC
LIMIT 10;
```

### Verify Indexing Performance
```sql
-- Check that indexes are being used
EXPLAIN ANALYZE
SELECT i.* FROM invoices i 
WHERE i.pos_receipt_id IS NOT NULL 
LIMIT 100;

EXPLAIN ANALYZE
SELECT s.* FROM sales s 
WHERE s.pos_receipt_id IS NOT NULL 
LIMIT 100;
```

---

## 🚀 Running Tests

### Run All Tests
```bash
# Backend
cd apps/backend
pytest app/tests/ -v -k "pos"

# Frontend
cd apps/tenant
npm run test

# E2E
npx playwright test
```

### Run Specific Test
```bash
# Backend
pytest app/tests/test_pos_checkout.py::test_invoice_creation -v

# Frontend
npm run test -- CheckoutSummary.test.tsx
```

### Run with Coverage
```bash
# Backend
pytest --cov=app.modules.pos app/tests/ -v

# Frontend
npm run test -- --coverage
```

---

## 📈 Performance Testing

### Load Test Checkout Endpoint
```bash
# Using Apache Bench
ab -n 1000 -c 10 -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/tenant/pos/receipts/id/checkout

# Using wrk
wrk -t4 -c100 -d30s \
  -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/tenant/pos/receipts/id/checkout
```

### Expected Performance
- Checkout should complete in < 500ms
- Document creation in < 200ms
- Database inserts should use indexes

---

## 🐛 Debugging

### Enable Debug Logging
```python
# In app/modules/pos/application/invoice_integration.py
logger.setLevel(logging.DEBUG)

# Or in .env
LOG_LEVEL=DEBUG
```

### Check Response Details
```javascript
// In browser console
const response = await payReceipt(receiptId, payments)
console.log('Full response:', response)
console.log('Documents created:', response.documents_created)
```

### Database Debugging
```sql
-- Check if transaction failed
SELECT * FROM pg_stat_activity WHERE state != 'idle';

-- Check recent errors
SELECT * FROM pg_stat_statements ORDER BY calls DESC LIMIT 10;
```

---

## ✅ Checklist for Testing

- [ ] Unit tests passing (backend)
- [ ] Unit tests passing (frontend)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Database queries optimized
- [ ] No N+1 query problems
- [ ] Error handling tested
- [ ] Module disable/enable tested
- [ ] All payment methods tested
- [ ] Return flow tested
- [ ] Performance acceptable

---

