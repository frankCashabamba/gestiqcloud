"""
INVOICING MODULE: Use Cases para facturación.

Implementa:
- Creación de facturas (desde POS o manualmente)
- Generación de PDFs (Jinja2 + WeasyPrint)
- Envío por email (SMTP/SendGrid)
- Tracking de pagos
- Numeración secuencial
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CreateInvoiceUseCase:
    """Crea factura desde recibo POS o manualmente."""

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
            "issued_at": datetime.utcnow(),
            "due_date": due_date or datetime.utcnow(),
        }


class GenerateInvoicePDFUseCase:
    """Genera PDF de factura usando Jinja2 + WeasyPrint."""

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
        """Genera PDF de factura. Returns PDF bytes."""
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
                "<h2>Factura {{ invoice_number }}</h2>"
                "<p>Cliente: {{ customer_name or 'N/A' }}</p>"
                "<p>Fecha: {{ issued_at }}</p>"
                "<table border='1' cellpadding='5'><tr><th>Descripción</th><th>Cant</th>"
                "<th>P.Unit</th><th>Total</th></tr>"
                "{% for l in lines %}<tr><td>{{ l.description }}</td>"
                "<td>{{ l.qty }}</td><td>{{ l.unit_price }}</td>"
                "<td>{{ l.amount }}</td></tr>{% endfor %}</table>"
                "<p>Subtotal: {{ subtotal }}</p>"
                "<p>IVA: {{ tax }}</p>"
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
    """Envía factura por email con PDF adjunto."""

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
        """Envía factura por email usando el servicio de correo configurado."""
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
                "sent_at": datetime.utcnow(),
                "recipient": recipient_email,
                "status": "skipped",
                "reason": "email_not_configured",
            }

        msg = EmailMessage()
        msg["Subject"] = f"Factura {invoice_number} - {company_name}".strip()
        msg["From"] = from_email
        msg["To"] = recipient_email
        msg.set_content(
            f"Estimado cliente,\n\n"
            f"Adjuntamos la factura {invoice_number}.\n\n"
            f"Atentamente,\n{company_name}"
        )
        msg.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"factura_{invoice_number}.pdf",
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
                "sent_at": datetime.utcnow(),
                "recipient": recipient_email,
                "status": "sent",
            }
        except Exception as e:
            logger.error("Failed to send invoice email: %s", e)
            return {
                "invoice_id": invoice_id,
                "sent_at": datetime.utcnow(),
                "recipient": recipient_email,
                "status": "failed",
                "error": str(e),
            }


class MarkInvoiceAsPaidUseCase:
    """Marca factura como pagada."""

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
            "paid_at": payment_date or datetime.utcnow(),
            "paid_amount": paid_amount,
            "payment_method": payment_method,
            "payment_ref": payment_ref,
        }


class CreateInvoiceFromPOSReceiptUseCase:
    """Crea factura automáticamente desde recibo POS."""

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
