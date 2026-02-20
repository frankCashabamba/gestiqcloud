"""Tests for Invoicing module use cases."""

import os
import pytest

pytestmark = pytest.mark.no_db
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.invoicing.application.use_cases import (
    CreateInvoiceUseCase,
    MarkInvoiceAsPaidUseCase,
    CreateInvoiceFromPOSReceiptUseCase,
    SendInvoiceEmailUseCase,
)


class TestCreateInvoiceUseCase:
    def test_create_invoice_calculates_total(self):
        uc = CreateInvoiceUseCase()
        result = uc.execute(
            invoice_number="FAC-2026-001",
            lines=[{"description": "Item 1", "qty": 2, "unit_price": 10.0}],
            subtotal=Decimal("20.00"),
            tax=Decimal("4.20"),
        )
        assert result["total"] == Decimal("24.20")
        assert result["status"] == "draft"
        assert result["number"] == "FAC-2026-001"

    def test_create_invoice_with_customer(self):
        cid = uuid4()
        uc = CreateInvoiceUseCase()
        result = uc.execute(
            invoice_number="FAC-2026-002",
            customer_id=cid,
            lines=[],
            subtotal=Decimal("100"),
            tax=Decimal("21"),
        )
        assert result["customer_id"] == cid
        assert result["total"] == Decimal("121")

    def test_create_invoice_with_notes(self):
        uc = CreateInvoiceUseCase()
        result = uc.execute(
            invoice_number="FAC-2026-003",
            lines=[],
            subtotal=Decimal("0"),
            tax=Decimal("0"),
            notes="Urgent delivery",
        )
        assert result["notes"] == "Urgent delivery"
        assert result["total"] == Decimal("0")

    def test_create_invoice_returns_uuid(self):
        uc = CreateInvoiceUseCase()
        result = uc.execute(
            invoice_number="FAC-2026-004",
            lines=[],
            subtotal=Decimal("50"),
            tax=Decimal("10.50"),
        )
        assert isinstance(result["invoice_id"], UUID)
        assert result["issued_at"] is not None


class TestMarkInvoiceAsPaidUseCase:
    def test_mark_paid(self):
        uc = MarkInvoiceAsPaidUseCase()
        inv_id = uuid4()
        result = uc.execute(
            invoice_id=inv_id,
            paid_amount=Decimal("121.00"),
            payment_method="card",
            payment_ref="TXN-123",
        )
        assert result["status"] == "paid"
        assert result["invoice_id"] == inv_id
        assert result["payment_method"] == "card"
        assert result["payment_ref"] == "TXN-123"
        assert result["paid_amount"] == Decimal("121.00")
        assert result["paid_at"] is not None

    def test_mark_paid_no_ref(self):
        uc = MarkInvoiceAsPaidUseCase()
        result = uc.execute(
            invoice_id=uuid4(),
            paid_amount=Decimal("50"),
            payment_method="cash",
        )
        assert result["status"] == "paid"
        assert result["payment_ref"] is None

    def test_mark_paid_custom_date(self):
        uc = MarkInvoiceAsPaidUseCase()
        dt = datetime(2026, 1, 15, 10, 30)
        result = uc.execute(
            invoice_id=uuid4(),
            paid_amount=Decimal("200"),
            payment_method="transfer",
            payment_date=dt,
        )
        assert result["paid_at"] == dt


class TestCreateInvoiceFromPOSReceiptUseCase:
    def test_creates_invoice_from_receipt(self):
        uc = CreateInvoiceFromPOSReceiptUseCase()
        rid = uuid4()
        result = uc.execute(
            receipt_id=rid,
            receipt_number="REC-001",
            lines=[],
            subtotal=Decimal("50"),
            tax=Decimal("10.50"),
        )
        assert result["invoice_number"] == "FAC-REC-001"
        assert result["total"] == Decimal("60.50")
        assert result["receipt_id"] == rid
        assert result["status"] == "draft"

    def test_creates_invoice_with_customer(self):
        uc = CreateInvoiceFromPOSReceiptUseCase()
        cid = uuid4()
        result = uc.execute(
            receipt_id=uuid4(),
            receipt_number="REC-002",
            lines=[{"description": "Coffee", "qty": 1, "unit_price": 3.50}],
            subtotal=Decimal("3.50"),
            tax=Decimal("0.74"),
            customer_id=cid,
        )
        assert result["customer_id"] == cid
        assert result["total"] == Decimal("4.24")


class TestSendInvoiceEmailUseCase:
    def test_send_email_not_configured(self):
        """When EMAIL_HOST is not set, should return skipped status."""
        old_host = os.environ.pop("EMAIL_HOST", None)
        old_from = os.environ.pop("DEFAULT_FROM_EMAIL", None)
        try:
            uc = SendInvoiceEmailUseCase()
            result = uc.execute(
                invoice_id=uuid4(),
                invoice_number="FAC-001",
                recipient_email="client@example.com",
                pdf_bytes=b"fake pdf",
            )
            assert result["status"] == "skipped"
            assert result["reason"] == "email_not_configured"
            assert result["recipient"] == "client@example.com"
        finally:
            if old_host:
                os.environ["EMAIL_HOST"] = old_host
            if old_from:
                os.environ["DEFAULT_FROM_EMAIL"] = old_from
