"""
INVOICING: Tenant Endpoints
Create invoices, send emails, track payments
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope, require_permission
from app.db.rls import ensure_rls
from app.modules.invoicing.application.schemas import (
    CreateInvoiceRequest,
    CreateInvoiceFromReceiptRequest,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceSummaryResponse,
    MarkInvoiceAsPaidRequest,
    SendInvoiceEmailRequest,
    SendEmailResponse,
)
from app.modules.invoicing.application.use_cases import (
    CreateInvoiceFromPOSReceiptUseCase,
    CreateInvoiceUseCase,
    GenerateInvoicePDFUseCase,
    GetInvoiceUseCase,
    MarkInvoiceAsPaidUseCase,
    SendInvoiceEmailUseCase,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/invoicing",
    tags=["Invoicing"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("invoicing.view")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# ENDPOINTS: CREATE
# ============================================================================


@router.post("/invoices", response_model=dict)
def create_invoice(
    payload: CreateInvoiceRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create invoice manually."""
    try:
        # Calculate totals
        subtotal = Decimal("0")
        tax = Decimal("0")
        for line in payload.lines:
            subtotal += line.amount
            tax += line.amount * line.tax_rate

        use_case = CreateInvoiceUseCase()
        invoice_data = use_case.execute(
            invoice_number=f"INV-{uuid4()}",  # TODO: Use NumberingService
            customer_id=payload.customer_id,
            lines=[l.dict() for l in payload.lines],
            subtotal=subtotal,
            tax=tax,
            notes=payload.notes,
            due_date=None,  # TODO: Calculate from due_days
        )

        # TODO: Persist to DB
        # invoice = Invoice(**invoice_data)
        # db.add(invoice)
        # db.commit()

        logger.info(f"Invoice {invoice_data['number']} created")
        return invoice_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating invoice")
        raise HTTPException(status_code=500, detail="Error al crear factura")


@router.post("/invoices/from-receipt", response_model=dict)
def create_invoice_from_receipt(
    payload: CreateInvoiceFromReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create invoice from POS receipt."""
    try:
        # TODO: Fetch receipt from DB
        # receipt = db.query(POSReceipt).filter(POSReceipt.id == payload.receipt_id).first()

        use_case = CreateInvoiceFromPOSReceiptUseCase()
        invoice_data = use_case.execute(
            receipt_id=payload.receipt_id,
            receipt_number="TKT-001",  # TODO: From receipt
            lines=[],  # TODO: From receipt lines
            subtotal=Decimal("0"),  # TODO: From receipt
            tax=Decimal("0"),  # TODO: From receipt
            customer_id=payload.customer_id,
        )

        logger.info(f"Invoice created from receipt {payload.receipt_id}")
        return invoice_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error creating invoice from receipt")
        raise HTTPException(status_code=500, detail="Error")


# ============================================================================
# ENDPOINTS: SEND
# ============================================================================


@router.post("/invoices/{invoice_id}/send", response_model=SendEmailResponse)
def send_invoice_email(
    invoice_id: UUID,
    payload: SendInvoiceEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send invoice by email with PDF attachment."""
    try:
        # TODO: Fetch invoice from DB
        # invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        # Generate PDF
        use_case_pdf = GenerateInvoicePDFUseCase()
        pdf_bytes = use_case_pdf.execute(
            invoice_id=invoice_id,
            invoice_number="INV-001",  # TODO: From invoice
            customer_name="Customer",  # TODO: From invoice
            lines=[],  # TODO: From invoice
            subtotal=Decimal("0"),  # TODO: From invoice
            tax=Decimal("0"),  # TODO: From invoice
            total=Decimal("0"),  # TODO: From invoice
            issued_at=datetime.utcnow(),
            company_name="Company",  # TODO: From settings
            company_logo_url=None,
        )

        # Send email
        use_case_send = SendInvoiceEmailUseCase()
        result = use_case_send.execute(
            invoice_id=invoice_id,
            invoice_number="INV-001",  # TODO: From invoice
            recipient_email=payload.recipient_email,
            pdf_bytes=pdf_bytes,
            template=payload.template,
        )

        # TODO: Update invoice status
        # db.query(Invoice).filter(Invoice.id == invoice_id).update({
        #     "status": "sent",
        #     "sent_at": datetime.utcnow()
        # })
        # db.commit()

        logger.info(f"Invoice {invoice_id} sent to {payload.recipient_email}")
        return {
            "invoice_id": invoice_id,
            "sent_at": datetime.utcnow(),
            "recipient": payload.recipient_email,
            "status": "sent",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error sending invoice")
        raise HTTPException(status_code=500, detail="Error al enviar factura")


# ============================================================================
# ENDPOINTS: PAYMENTS
# ============================================================================


@router.post("/invoices/{invoice_id}/mark-paid", response_model=dict)
def mark_invoice_paid(
    invoice_id: UUID,
    payload: MarkInvoiceAsPaidRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark invoice as paid."""
    try:
        use_case = MarkInvoiceAsPaidUseCase()
        result = use_case.execute(
            invoice_id=invoice_id,
            paid_amount=payload.paid_amount,
            payment_method=payload.payment_method,
            payment_ref=payload.payment_ref,
        )

        # TODO: Update invoice + create payment record
        # db.query(Invoice).filter(Invoice.id == invoice_id).update({
        #     "status": "paid",
        #     "paid_at": datetime.utcnow()
        # })
        # db.commit()

        logger.info(f"Invoice {invoice_id} marked as paid")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error marking invoice as paid")
        raise HTTPException(status_code=500, detail="Error")


# ============================================================================
# ENDPOINTS: LIST & GET
# ============================================================================


@router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    request: Request,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List invoices with pagination."""
    try:
        # TODO: Fetch from DB with pagination
        # invoices = db.query(Invoice).offset(skip).limit(limit).all()
        # total_count = db.query(Invoice).count()

        return {
            "invoices": [],
            "total_count": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
        }

    except Exception as e:
        logger.exception("Error listing invoices")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/invoices/{invoice_id}", response_model=dict)
def get_invoice(
    invoice_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get invoice details."""
    try:
        use_case = GetInvoiceUseCase()
        invoice = use_case.execute(invoice_id=invoice_id)

        # TODO: Fetch from DB
        # invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()

        return invoice

    except Exception as e:
        logger.exception("Error fetching invoice")
        raise HTTPException(status_code=500, detail="Error")


@router.get("/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Download invoice as PDF."""
    try:
        # TODO: Fetch invoice from DB
        use_case = GenerateInvoicePDFUseCase()
        pdf_bytes = use_case.execute(
            invoice_id=invoice_id,
            invoice_number="INV-001",
            customer_name="Customer",
            lines=[],
            subtotal=Decimal("0"),
            tax=Decimal("0"),
            total=Decimal("0"),
            issued_at=datetime.utcnow(),
            company_name="Company",
        )

        from fastapi.responses import StreamingResponse
        import io

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice-{invoice_id}.pdf"},
        )

    except Exception as e:
        logger.exception("Error generating PDF")
        raise HTTPException(status_code=500, detail="Error")
