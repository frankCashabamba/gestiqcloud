# SPRINT 1: DB PERSISTENCE LAYER INTEGRATION

**Status:** Endpoints ready for DB integration  
**Effort:** 2-3 hours to wire everything

---

## 🔗 INTEGRATION CHECKLIST

### Identity Module
```python
# File: apps/backend/app/modules/identity/interface/http/tenant_auth.py

DONE:
✓ LoginUseCase.execute() completes
✓ RefreshTokenUseCase.execute() completes
✓ LogoutUseCase.execute() completes
✓ ChangePasswordUseCase.execute() completes

TODO (IN ENDPOINTS):
□ Line 150-155: Replace None with actual services
  - token_service = JWTService()  # from DI
  - password_hasher = PasswordHasher()  # from DI
  - rate_limiter = RateLimiter()  # from DI
  - refresh_repo = RefreshTokenRepo()  # from DI

□ Line 157-170: Persist updated password
  - user.password_hash = result["new_password_hash"]
  - db.commit()
```

### POS Module
```python
# File: apps/backend/app/modules/pos/interface/http/tenant_pos.py

TODO (IN ENDPOINTS):
□ open_shift() lines 103-112
  - shift = POSShift(**shift_data)
  - db.add(shift)
  - db.commit()
  - db.refresh(shift)

□ create_receipt() lines 154-172
  - receipt = POSReceipt(**receipt_data)
  - db.add(receipt)
  - for line in payload.lines:
  -     db.add(POSReceiptLine(receipt_id=receipt.id, **line.dict()))
  - db.commit()

□ checkout() lines 209-243
  - receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
  - receipt.status = "paid"
  - receipt.paid_at = datetime.utcnow()
  - inv_svc = InventoryCostingService(db)
  - inv_svc.deduct_stock(...)
  - acct_svc = AccountingService(db)
  - acct_svc.create_entry_from_receipt(receipt_id)
  - db.commit()

□ get_shift_summary() lines 294-318
  - Fetch shift from DB
  - Calculate totals from receipts
  - Return summary
```

### Invoicing Module
```python
# File: apps/backend/app/modules/invoicing/interface/http/tenant_invoicing.py

TODO (IN ENDPOINTS):
□ create_invoice() lines 71-100
  - invoice = Invoice(**invoice_data)
  - db.add(invoice)
  - db.commit()

□ send_invoice_email() lines 150-199
  - invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
  - db.query(Invoice).filter(Invoice.id == invoice_id).update({
      "status": "sent",
      "sent_at": datetime.utcnow()
    })
  - db.commit()

□ mark_invoice_paid() lines 226-254
  - db.query(Invoice).filter(Invoice.id == invoice_id).update({
      "status": "paid",
      "paid_at": datetime.utcnow()
    })
  - Create payment record in db
  - db.commit()
```

### Inventory Module
```python
# File: apps/backend/app/modules/inventory/interface/http/tenant_inventory.py

TODO (IN ENDPOINTS):
□ receive_stock() lines 81-109
  - db.add(StockReceipt(**receipt))
  - for line: db.add(StockMove(...))
  - db.commit()

□ adjust_stock() lines 131-161
  - db.add(StockMove(**move))
  - db.commit()

□ transfer_stock() lines 183-213
  - Update warehouse1 stock
  - Update warehouse2 stock
  - Create moves for both
  - db.commit()
```

### Sales Module
```python
# File: apps/backend/app/modules/sales/interface/http/tenant_sales.py

TODO (IN ENDPOINTS):
□ create_sales_order() lines 88-118
  - order = SalesOrder(**order_data)
  - db.add(order)
  - for line: db.add(SalesOrderLine(...))
  - db.commit()

□ approve_sales_order() lines 140-169
  - db.query(SalesOrder).filter(SalesOrder.id == order_id).update({
      "status": "approved",
      "approved_at": datetime.utcnow()
    })
  - db.commit()

□ create_invoice_from_order() lines 191-222
  - Similar to invoicing
  - db.query(SalesOrder).filter(SalesOrder.id == order_id).update({
      "status": "invoiced",
      "invoice_id": invoice_data["invoice_id"]
    })
  - db.commit()
```

---

## 📋 DB MODELS VERIFICATION

Check if these tables exist in PostgreSQL:

```sql
-- Identity
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('users', 'user_roles', 'refresh_tokens');

-- POS
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('pos_registers', 'pos_shifts', 'pos_receipts', 'pos_receipt_lines', 'pos_payments');

-- Invoicing
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('invoices', 'invoice_lines', 'payments');

-- Inventory
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('warehouses', 'stock_items', 'stock_moves');

-- Sales
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('sales_orders', 'sales_order_lines');

-- Accounting
SELECT table_name FROM information_schema.tables WHERE table_schema='public' 
  AND table_name IN ('journal_entries', 'journal_entry_lines', 'chart_of_accounts');
```

If missing, create migrations:
```bash
cd apps/backend
alembic revision -m "add identity models"
alembic revision -m "add pos models"
alembic revision -m "add invoicing models"
alembic revision -m "add inventory models"
alembic revision -m "add sales models"
alembic revision -m "add accounting models"

alembic upgrade head
```

---

## 🔌 DEPENDENCY INJECTION

Create service providers (FastAPI dependency):

```python
# File: apps/backend/app/core/services.py

from fastapi import Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.inventory_service import InventoryCostingService
from app.services.accounting_service import AccountingService
from app.services.email_service import EmailService
from app.services.pdf_service import PDFService

def get_inventory_service(db: Session = Depends(get_db)) -> InventoryCostingService:
    return InventoryCostingService(db)

def get_accounting_service(db: Session = Depends(get_db)) -> AccountingService:
    return AccountingService(db)

def get_email_service() -> EmailService:
    return EmailService(api_key=settings.sendgrid_api_key)

def get_pdf_service() -> PDFService:
    return PDFService()
```

Then use in endpoints:
```python
@router.post("/receipts/{id}/checkout")
def checkout(
    ...,
    inventory_service: InventoryCostingService = Depends(get_inventory_service),
    accounting_service: AccountingService = Depends(get_accounting_service),
):
    inv_svc.deduct_stock(...)
    acct_svc.create_entry_from_receipt(...)
```

---

## 🎯 INTEGRATION ORDER

1. **Identity** (foundation - needed for auth)
   - Wire JWTService, PasswordHasher, RateLimiter
   - Test: POST /auth/login → 200
   - Requires: users table

2. **POS** (core business)
   - Wire InventoryCostingService, AccountingService
   - Test: POST /pos/shifts/open → 201
   - Test: POST /pos/receipts/{id}/checkout → 200 (with stock + journal)
   - Requires: pos_*, warehouses, stock_items, stock_moves, journal_entries tables

3. **Invoicing** (dependent on POS)
   - Wire EmailService, PDFService
   - Test: POST /invoicing/invoices/{id}/send → 200
   - Requires: invoices, invoice_lines, payments tables

4. **Inventory** (dependent on POS)
   - Already integrated via InventoryCostingService
   - Test: POST /inventory/stock/receive → 200
   - Requires: warehouses, stock_items, stock_moves tables

5. **Sales** (dependent on Invoicing)
   - Wire to Invoicing service
   - Test: POST /sales/orders → 201
   - Test: POST /sales/orders/{id}/invoice → 201
   - Requires: sales_orders, sales_order_lines tables

---

## ✅ INTEGRATION TEMPLATE

Replace TODOs in endpoints like this:

**BEFORE:**
```python
def checkout(...):
    use_case = CheckoutReceiptUseCase()
    result = use_case.execute(...)
    
    # TODO: Update receipt
    # TODO: Deduct stock
    # TODO: Create journal entry
    
    logger.info(f"Receipt {receipt_id} paid")
    return result
```

**AFTER:**
```python
def checkout(
    receipt_id: UUID,
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    inv_svc: InventoryCostingService = Depends(get_inventory_service),
    acct_svc: AccountingService = Depends(get_accounting_service),
):
    """Pay receipt + deduct stock + create journal entry."""
    try:
        use_case = CheckoutReceiptUseCase()
        result = use_case.execute(
            receipt_id=receipt_id,
            payments=payload.payments,
            warehouse_id=payload.warehouse_id,
        )
        
        # 1. Update receipt
        receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        receipt.status = "paid"
        receipt.paid_at = datetime.utcnow()
        
        # 2. Deduct stock
        for line in receipt.lines:
            cogs = inv_svc.deduct_stock(
                product_id=line.product_id,
                warehouse_id=result.get("warehouse_id"),
                qty=line.qty,
            )
            # Update line with COGS info
            line.cogs_unit = cogs["cogs_unit"]
            line.cogs_total = cogs["cogs_total"]
        
        # 3. Create journal entry
        acct_svc.create_entry_from_receipt(receipt_id=receipt_id)
        
        db.commit()
        audit_event(request, "pos.receipt.paid", receipt_id)
        
        logger.info(f"Receipt {receipt_id} paid with stock + accounting")
        return result
    
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.exception("Error during checkout")
        raise HTTPException(status_code=500, detail="Error")
```

---

## 🧪 MANUAL TEST FLOW

After integration:

```
1. POST /auth/login
   ├─ Get access_token + refresh_token
   └─ Save access_token for next calls

2. POST /pos/shifts/open
   ├─ Get shift_id
   └─ Save for next calls

3. POST /pos/receipts
   ├─ Create receipt in DB
   ├─ Get receipt_id
   └─ Save for next calls

4. POST /pos/receipts/{id}/checkout
   ├─ Update receipt.status = "paid"
   ├─ Deduct stock from inventory
   ├─ Create journal entry
   └─ Verify all 3 operations in DB

5. POST /pos/shifts/{id}/close
   ├─ Calculate variance from receipts
   ├─ Close shift
   └─ Verify shift.status = "closed"

6. POST /invoicing/invoices/from-receipt
   ├─ Create invoice from receipt
   ├─ Get invoice_id
   └─ Verify link in DB

7. POST /invoicing/invoices/{id}/send
   ├─ Generate PDF
   ├─ Send email
   └─ Update invoice.status = "sent"

8. POST /sales/orders
   ├─ Create order
   ├─ Get order_id
   └─ Verify customer linked

9. PATCH /sales/orders/{id}/approve
   ├─ Update order.status = "approved"
   └─ Verify timestamp

10. POST /sales/orders/{id}/invoice
    ├─ Create invoice from order
    ├─ Update order.status = "invoiced"
    └─ Verify link in DB
```

---

## 📊 SUCCESS CRITERIA

```
✓ All 20 endpoints persist to DB
✓ All relationships created correctly
✓ Stock movements tracked
✓ Journal entries auto-created
✓ Emails sent (or stubbed)
✓ PDFs generated (or stubbed)
✓ No SQL errors in logs
✓ Manual test flow completes
✓ Postman collection passes all tests
```

---

**READY FOR DB WIRING** 🔌
