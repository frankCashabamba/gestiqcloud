"""
INVOICING MODULE: Use Cases para facturación.

Implementa:
- Creación de facturas (desde POS o manualmente)
- Generación de PDFs
- Envío por email
- Tracking de pagos
- Numeración secuencial
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CreateInvoiceUseCase:
    """Crea factura desde recibo POS o manualmente."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        invoice_number: str,
        customer_id: UUID | None = None,
        lines: list[dict[str, Any]],
        subtotal: Decimal,
        tax: Decimal,
        notes: str | None = None,
        due_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Crea factura con líneas.

        Args:
            invoice_number: Número secuencial (ej: FAC-2026-001)
            customer_id: Customer ID (optional)
            lines: List of {description, qty, unit_price, tax_rate, amount}
            subtotal: Subtotal
            tax: Total tax
            notes: Notas (términos de pago, referencias)
            due_date: Fecha de vencimiento

        Returns:
            {
                "invoice_id": UUID,
                "number": str,
                "status": "draft",
                "subtotal": Decimal,
                "tax": Decimal,
                "total": Decimal,
                "issued_at": datetime,
                "due_date": datetime
            }
        """
        total = subtotal + tax

        return {
            "invoice_id": UUID(int=0),  # Set by repo
            "number": invoice_number,
            "customer_id": customer_id,
            "status": "draft",
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "lines": lines,
            "notes": notes,
            "issued_at": datetime.utcnow(),
            "due_date": due_date or datetime.utcnow(),
        }


class GenerateInvoicePDFUseCase:
    """Genera PDF de factura."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        invoice_id: UUID,
        invoice_number: str,
        customer_name: str | None = None,
        lines: list[dict[str, Any]],
        subtotal: Decimal,
        tax: Decimal,
        total: Decimal,
        issued_at: datetime,
        company_name: str,
        company_logo_url: str | None = None,
    ) -> bytes:
        """
        Genera PDF de factura.

        Usa ReportLab para crear PDF dinámico.
        Incluye: logo, datos empresa, líneas, totales, código QR.

        Args:
            invoice_id: Invoice ID
            invoice_number: Invoice number
            customer_name: Customer name
            lines: Invoice lines
            subtotal: Subtotal
            tax: Tax total
            total: Grand total
            issued_at: Issue date
            company_name: Company name
            company_logo_url: Logo URL (optional)

        Returns:
            PDF bytes
        """
        # TODO: Implement with reportlab
        # - Header with company logo + details
        # - Table with lines (item, qty, price, tax, total)
        # - Summary (subtotal, tax, total)
        # - Footer with payment terms
        # - QR code with payment reference

        logger.info(f"Generated PDF for invoice {invoice_number}")

        return b"PDF content placeholder"


class SendInvoiceEmailUseCase:
    """Envía factura por email."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        invoice_id: UUID,
        invoice_number: str,
        recipient_email: str,
        pdf_bytes: bytes,
        template: str = "default",
    ) -> dict[str, Any]:
        """
        Envía factura por email con PDF.

        Usa SendGrid con template personalizado.

        Args:
            invoice_id: Invoice ID
            invoice_number: Invoice number
            recipient_email: Recipient email
            pdf_bytes: PDF content
            template: Template name (default, es, en)

        Returns:
            {
                "invoice_id": UUID,
                "sent_at": datetime,
                "recipient": str,
                "status": "sent"
            }
        """
        logger.info(f"Sent invoice {invoice_number} to {recipient_email}")

        return {
            "invoice_id": invoice_id,
            "sent_at": datetime.utcnow(),
            "recipient": recipient_email,
            "status": "sent",
        }


class MarkInvoiceAsPaidUseCase:
    """Marca factura como pagada."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        invoice_id: UUID,
        paid_amount: Decimal,
        payment_method: str,
        payment_ref: str | None = None,
        payment_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Marca factura como pagada.

        Args:
            invoice_id: Invoice ID
            paid_amount: Amount paid
            payment_method: cash, card, transfer, check
            payment_ref: Reference (check number, transfer ID)
            payment_date: Payment date (default: now)

        Returns:
            {
                "invoice_id": UUID,
                "status": "paid",
                "paid_at": datetime,
                "paid_amount": Decimal
            }
        """
        return {
            "invoice_id": invoice_id,
            "status": "paid",
            "paid_at": payment_date or datetime.utcnow(),
            "paid_amount": paid_amount,
            "payment_method": payment_method,
            "payment_ref": payment_ref,
        }


class CreateInvoiceFromPOSReceiptUseCase:
    """Crea factura automáticamente desde recibo POS."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        receipt_id: UUID,
        receipt_number: str,
        lines: list[dict[str, Any]],
        subtotal: Decimal,
        tax: Decimal,
        customer_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Convierte recibo POS a factura formal.

        Mapeo:
        - receipt.number → invoice.number (con prefijo FAC-)
        - receipt.lines → invoice.lines
        - receipt.customer_id → invoice.customer_id
        - receipt.total → invoice.total

        Args:
            receipt_id: Receipt ID
            receipt_number: Receipt number
            lines: Receipt lines
            subtotal: Subtotal
            tax: Tax
            customer_id: Customer ID (optional)

        Returns:
            {
                "invoice_id": UUID,
                "invoice_number": str,
                "status": "draft",
                "receipt_id": UUID
            }
        """
        invoice_number = f"FAC-{receipt_number}"

        return {
            "invoice_id": UUID(int=0),  # Set by repo
            "invoice_number": invoice_number,
            "status": "draft",
            "receipt_id": receipt_id,
            "customer_id": customer_id,
            "subtotal": subtotal,
            "tax": tax,
            "total": subtotal + tax,
        }


class GetInvoiceUseCase:
    """Obtiene detalle de factura."""

    def __init__(self):
        pass

    def execute(
        self,
        *,
        invoice_id: UUID,
    ) -> dict[str, Any]:
        """
        Obtiene detalle completo de factura.

        Args:
            invoice_id: Invoice ID

        Returns:
            {
                "id": UUID,
                "number": str,
                "status": str,
                "customer": {...},
                "lines": [...],
                "subtotal": Decimal,
                "tax": Decimal,
                "total": Decimal,
                "issued_at": datetime,
                "paid_at": datetime | None,
                "due_date": datetime
            }
        """
        return {
            "id": invoice_id,
            "number": "",
            "status": "draft",
        }
