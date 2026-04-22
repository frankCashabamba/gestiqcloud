"""
Invoicing module use cases.

Implements:
- Invoice creation (from POS or manually)
- PDF generation (Jinja2 + WeasyPrint)
- Email delivery (SMTP/SendGrid)
- Payment tracking
- Sequential numbering
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CreateInvoiceUseCase:
    """Create an invoice from a POS receipt or manually."""

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
        total = subtotal + tax
        return {
            "invoice_id": UUID(int=0),
            "number": invoice_number,
            "customer_id": customer_id,
            "status": "draft",
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "lines": lines,
            "notes": notes,
            "issued_at": datetime.now(UTC),
            "due_date": due_date or datetime.now(UTC),
        }


class GenerateInvoicePDFUseCase:
    """Generate an invoice PDF using Jinja2 + WeasyPrint."""

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
        """Generate an invoice PDF and return the bytes."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from weasyprint import HTML

        base_dir = Path(__file__).resolve().parents[3]  # apps/backend/app
        tmpl_dir = base_dir / "templates" / "pdf"

        if not tmpl_dir.exists():
            tmpl_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(tmpl_dir)),
            autoescape=select_autoescape(["html"]),
        )

        tmpl_name = os.getenv("INVOICE_PDF_TEMPLATE", "invoice_base.html")
        try:
            template = env.get_template(tmpl_name)
        except Exception:
            logger.warning("Template %s not found, using inline fallback", tmpl_name)
            from jinja2 import Template

            template = Template(
                "<html><body>"
                "<h1>{{ company_name }}</h1>"
                "<h2>Invoice {{ invoice_number }}</h2>"
                "<p>Customer: {{ customer_name or 'N/A' }}</p>"
                "<p>Date: {{ issued_at }}</p>"
                "<table border='1' cellpadding='5'><tr><th>Description</th><th>Qty</th>"
                "<th>Unit price</th><th>Total</th></tr>"
                "{% for l in lines %}<tr><td>{{ l.description }}</td>"
                "<td>{{ l.qty }}</td><td>{{ l.unit_price }}</td>"
                "<td>{{ l.amount }}</td></tr>{% endfor %}</table>"
                "<p>Subtotal: {{ subtotal }}</p>"
                "<p>Tax: {{ tax }}</p>"
                "<p><strong>Total: {{ total }}</strong></p>"
                "</body></html>"
            )

        html = template.render(
            invoice_number=invoice_number,
            customer_name=customer_name,
            lines=lines,
            subtotal=subtotal,
            tax=tax,
            total=total,
            issued_at=issued_at,
            company_name=company_name,
            company_logo_url=company_logo_url,
        )

        pdf_bytes = HTML(string=html).write_pdf()
        logger.info("Generated PDF for invoice %s (%d bytes)", invoice_number, len(pdf_bytes))
        return pdf_bytes


class SendInvoiceEmailUseCase:
    """Send an invoice by email with a PDF attachment."""

    def execute(
        self,
        *,
        invoice_id: UUID,
        invoice_number: str,
        recipient_email: str,
        pdf_bytes: bytes,
        template: str = "default",
        company_name: str = "",
    ) -> dict[str, Any]:
        """Send an invoice by email using the configured mail service."""
        import smtplib
        from email.message import EmailMessage

        from_email = os.getenv("DEFAULT_FROM_EMAIL", "")
        smtp_host = os.getenv("EMAIL_HOST", "")
        smtp_port = int(os.getenv("EMAIL_PORT", "587"))
        smtp_user = os.getenv("EMAIL_HOST_USER", "")
        smtp_pass = os.getenv("EMAIL_HOST_PASSWORD", "")

        if not from_email or not smtp_host:
            logger.warning("Email not configured (EMAIL_HOST / DEFAULT_FROM_EMAIL missing)")
            return {
                "invoice_id": invoice_id,
                "sent_at": datetime.now(UTC),
                "recipient": recipient_email,
                "status": "skipped",
                "reason": "email_not_configured",
            }

        msg = EmailMessage()
        msg["Subject"] = f"Invoice {invoice_number} - {company_name}".strip()
        msg["From"] = from_email
        msg["To"] = recipient_email
        msg.set_content(
            f"Dear customer,\n\n"
            f"Attached is invoice {invoice_number}.\n\n"
            f"Regards,\n{company_name}"
        )
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"invoice_{invoice_number}.pdf",
        )

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                if smtp_port != 25:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info("Sent invoice %s to %s", invoice_number, recipient_email)
            return {
                "invoice_id": invoice_id,
                "sent_at": datetime.now(UTC),
                "recipient": recipient_email,
                "status": "sent",
            }
        except Exception as e:
            logger.error("Failed to send invoice email: %s", e)
            return {
                "invoice_id": invoice_id,
                "sent_at": datetime.now(UTC),
                "recipient": recipient_email,
                "status": "failed",
                "error": str(e),
            }


class MarkInvoiceAsPaidUseCase:
    """Mark an invoice as paid."""

    def execute(
        self,
        *,
        invoice_id: UUID,
        paid_amount: Decimal,
        payment_method: str,
        payment_ref: str | None = None,
        payment_date: datetime | None = None,
    ) -> dict[str, Any]:
        return {
            "invoice_id": invoice_id,
            "status": "paid",
            "paid_at": payment_date or datetime.now(UTC),
            "paid_amount": paid_amount,
            "payment_method": payment_method,
            "payment_ref": payment_ref,
        }


class CreateInvoiceFromPOSReceiptUseCase:
    """Automatically create an invoice from a POS receipt."""

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
        invoice_number = f"FAC-{receipt_number}"
        return {
            "invoice_id": UUID(int=0),
            "invoice_number": invoice_number,
            "status": "draft",
            "receipt_id": receipt_id,
            "customer_id": customer_id,
            "subtotal": subtotal,
            "tax": tax,
            "total": subtotal + tax,
        }
