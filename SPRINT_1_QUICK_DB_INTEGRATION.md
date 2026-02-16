# SPRINT 1: QUICK DB INTEGRATION (Copy-Paste Ready)

**Time estimate:** 1 hour to wire everything

---

## 1️⃣ CREATE SERVICES DI PROVIDER

**File:** Create `apps/backend/app/core/service_providers.py`

```python
"""Service dependency injection for FastAPI endpoints."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.services.accounting_service import AccountingService
from app.services.email_service import EmailService
from app.services.inventory_service import InventoryCostingService
from app.services.pdf_service import PDFService


def get_inventory_service(db: Session = Depends(get_db)) -> InventoryCostingService:
    """Provide InventoryCostingService."""
    return InventoryCostingService(db)


def get_accounting_service(db: Session = Depends(get_db)) -> AccountingService:
    """Provide AccountingService."""
    return AccountingService(db)


def get_email_service() -> EmailService:
    """Provide EmailService."""
    api_key = getattr(settings, "sendgrid_api_key", None)
    return EmailService(api_key=api_key)


def get_pdf_service() -> PDFService:
    """Provide PDFService."""
    return PDFService()
```

---

## 2️⃣ UPDATE POS CHECKOUT ENDPOINT (Main Integration Example)

**File:** `apps/backend/app/modules/pos/interface/http/tenant_pos.py`

Find and replace function:

```python
from app.core.service_providers import (
    get_accounting_service,
    get_inventory_service,
)

# ... existing code ...

@router.post("/receipts/{receipt_id}/checkout", response_model=dict)
def checkout(
    receipt_id: UUID,
    payload: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    inv_svc: InventoryCostingService = Depends(get_inventory_service),
    acct_svc: AccountingService = Depends(get_accounting_service),
):
    """
    Pay receipt (checkout) with full integration:
    1. Validate payments
    2. Deduct stock from inventory (FIFO/LIFO)
    3. Create journal entry in accounting
    4. Update receipt status to paid
    5. Calculate profit margin
    """
    try:
        # 1. Fetch receipt
        receipt = db.query(POSReceipt).filter(POSReceipt.id == receipt_id).first()
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        if receipt.status != "draft":
            raise HTTPException(
                status_code=400,
                detail=f"Receipt status {receipt.status}, must be draft"
            )

        # 2. Calculate totals
        total_paid = sum(
            Decimal(str(p.get("amount", 0))) for p in payload.payments
        )
        receipt_total = receipt.total  # From DB or calculated

        if total_paid < receipt_total:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient payment. Paid: {total_paid}, Required: {receipt_total}"
            )

        # 3. Record payments
        for payment in payload.payments:
            payment_record = POSPayment(
                id=uuid4(),
                receipt_id=receipt_id,
                method=payment.get("method"),
                amount=Decimal(str(payment.get("amount", 0))),
                ref=payment.get("ref"),
                paid_at=datetime.utcnow(),
            )
            db.add(payment_record)

        # 4. Deduct stock
        for line in receipt.lines:
            cogs_info = inv_svc.deduct_stock(
                product_id=line.product_id,
                warehouse_id=payload.warehouse_id or UUID(int=0),
                qty=Decimal(str(line.qty)),
            )
            
            # Update line with cost info
            line.cogs_unit = cogs_info.get("cogs_unit", Decimal("0"))
            line.cogs_total = cogs_info.get("cogs_total", Decimal("0"))
            
            # Calculate margin
            line_sales = line.qty * Decimal(str(line.unit_price))
            line.gross_profit = line_sales - line.cogs_total
            line.gross_margin_pct = (
                (line.gross_profit / line_sales * 100)
                if line_sales > 0
                else Decimal("0")
            )

        # 5. Create journal entry
        acct_svc.create_entry_from_receipt(receipt_id=receipt_id)

        # 6. Update receipt status
        receipt.status = "paid"
        receipt.paid_at = datetime.utcnow()

        # Commit everything
        db.commit()

        logger.info(f"Receipt {receipt_id} paid. Stock deducted. Journal entry created.")
        audit_event(request, "pos.receipt.paid", receipt_id)

        return {
            "receipt_id": receipt_id,
            "status": "paid",
            "paid_at": datetime.utcnow(),
            "total_paid": total_paid,
            "change": total_paid - receipt_total,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error during checkout")
        raise HTTPException(status_code=500, detail="Error al procesar pago")
```

---

## 3️⃣ UPDATE INVOICING SEND EMAIL ENDPOINT

**File:** `apps/backend/app/modules/invoicing/interface/http/tenant_invoicing.py`

```python
from app.core.service_providers import get_email_service, get_pdf_service

# ... existing code ...

@router.post("/invoices/{invoice_id}/send", response_model=SendEmailResponse)
def send_invoice_email(
    invoice_id: UUID,
    payload: SendInvoiceEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_svc: EmailService = Depends(get_email_service),
    pdf_svc: PDFService = Depends(get_pdf_service),
):
    """Send invoice by email with PDF attachment."""
    try:
        # Fetch invoice
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Generate PDF
        pdf_bytes = pdf_svc.generate_invoice_pdf(
            invoice_id=invoice.id,
            invoice_number=invoice.number,
            issue_date=invoice.issued_at,
            due_date=invoice.due_date,
            customer_info={
                "name": invoice.customer.name if invoice.customer else "N/A",
                "email": payload.recipient_email,
            },
            company_info={
                "name": "Your Company",
                "address": "123 Main St",
                "phone": "555-1234",
                "email": "info@company.com",
            },
            lines=[
                {
                    "item": line.description,
                    "qty": line.qty,
                    "price": line.unit_price,
                    "amount": line.amount,
                }
                for line in invoice.lines
            ],
            subtotal=invoice.subtotal,
            tax=invoice.tax,
            total=invoice.total,
        )

        # Send email
        email_result = email_svc.send_invoice(
            to_email=payload.recipient_email,
            invoice_number=invoice.number,
            customer_name=invoice.customer.name if invoice.customer else "Customer",
            amount=str(invoice.total),
            pdf_attachment=pdf_bytes,
            template="invoice_default",
        )

        # Update invoice status
        invoice.status = "sent"
        invoice.sent_at = datetime.utcnow()
        db.commit()

        logger.info(f"Invoice {invoice.number} sent to {payload.recipient_email}")
        audit_event(request, "invoice.sent", invoice_id)

        return {
            "invoice_id": invoice_id,
            "sent_at": datetime.utcnow(),
            "recipient": payload.recipient_email,
            "status": "sent",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error sending invoice")
        raise HTTPException(status_code=500, detail="Error al enviar factura")
```

---

## 4️⃣ UPDATE ALL OTHER ENDPOINTS (BATCH)

Use this pattern for remaining endpoints:

### POS - Open Shift
```python
@router.post("/shifts/open", response_model=ShiftResponse)
def open_shift(
    payload: OpenShiftRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        use_case = OpenShiftUseCase()
        shift_data = use_case.execute(
            register_id=payload.register_id,
            opening_float=payload.opening_float,
            cashier_id=_get_user_id(request),
        )

        # NEW: Persist
        shift = POSShift(**shift_data)
        db.add(shift)
        db.commit()
        db.refresh(shift)

        audit_event(request, "pos.shift.opened", shift.id)
        return shift

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
```

### POS - Create Receipt
```python
@router.post("/receipts", response_model=dict)
def create_receipt(
    payload: CreateReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        use_case = CreateReceiptUseCase()
        receipt_data = use_case.execute(...)

        # NEW: Persist receipt + lines
        receipt = POSReceipt(**receipt_data)
        db.add(receipt)
        
        for line in payload.lines:
            db.add(POSReceiptLine(
                receipt_id=receipt.id,
                **line.dict()
            ))
        
        db.commit()
        db.refresh(receipt)

        audit_event(request, "pos.receipt.created", receipt.id)
        return receipt

    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 5️⃣ ADD MISSING MODEL IMPORTS

**File:** `apps/backend/app/modules/pos/interface/http/tenant_pos.py`

Add at top:
```python
from app.models.core.pos import (
    POSPayment,
    POSReceipt,
    POSReceiptLine,
    POSShift,
)
```

**File:** `apps/backend/app/modules/invoicing/interface/http/tenant_invoicing.py`

Add at top:
```python
from app.models.core.invoicing import Invoice, InvoiceLine
```

**File:** `apps/backend/app/modules/sales/interface/http/tenant_sales.py`

Add at top:
```python
from app.models.core.sales import SalesOrder, SalesOrderLine
```

---

## 6️⃣ MIGRATION & VERIFICATION

```bash
# 1. Check if models exist
cd apps/backend
python -c "from app.models.core.pos import POSShift; print('Models OK')"

# 2. If missing, create migration
alembic revision --autogenerate -m "add sprint1 models"

# 3. Apply migration
alembic upgrade head

# 4. Verify tables
psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
```

---

## 🧪 QUICK TEST AFTER INTEGRATION

```bash
# Start server
cd apps/backend
uvicorn app.main:app --reload

# In Postman:
POST http://localhost:8000/api/v1/tenant/auth/login
{
  "email": "user@example.com",
  "password": "password123"
}

# Copy access_token, then:

POST http://localhost:8000/api/v1/tenant/pos/shifts/open
Headers: Authorization: Bearer <token>
{
  "register_id": "550e8400-e29b-41d4-a716-446655440000",
  "opening_float": 100
}

# Should return 201 with shift data from DB
```

---

## ✅ SUCCESS = 100% OF SPRINT 1

Once all endpoints wire to DB:
- [x] Use cases: 100%
- [x] Endpoints: 100%
- [x] Services: 100%
- [x] Schemas: 100%
- [x] DB integration: 100%
- [x] Manual testing: 100%

= **READY FOR SPRINT 2**

---

**TIME TO COMPLETE: 1 HOUR** ⚡
