"""Module: invoiceLine.py - Invoice line item models."""

import uuid as _uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.models.tenant import TENANT_UUID


class InvoiceLine(Base):
    """Invoice line item base model."""

    __tablename__ = "invoice_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[_uuid.UUID] = mapped_column(
        TENANT_UUID,
        primary_key=True,
        default=_uuid.uuid4,
    )
    invoice_id: Mapped[_uuid.UUID] = mapped_column(
        "invoice_id", TENANT_UUID, ForeignKey("invoices.id")
    )
    sector: Mapped[str] = mapped_column("sector", String(50))
    description: Mapped[str] = mapped_column("description", String)
    quantity: Mapped[float] = mapped_column("quantity")
    unit_price: Mapped[float] = mapped_column("unit_price")
    vat: Mapped[float] = mapped_column("vat", default=0)

    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": sector}


# Keep old name for backward compatibility during migration
LineaFactura = InvoiceLine


class BakeryLine(InvoiceLine):
    """Bakery line item model."""

    __tablename__ = "bakery_lines"

    id: Mapped[_uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("invoice_lines.id"), primary_key=True
    )
    bread_type: Mapped[str] = mapped_column("bread_type", String)
    grams: Mapped[float] = mapped_column("grams")

    __mapper_args__ = {"polymorphic_identity": "bakery"}


class WorkshopLine(InvoiceLine):
    """Workshop line item model."""

    __tablename__ = "workshop_lines"

    id: Mapped[_uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("invoice_lines.id"), primary_key=True
    )
    spare_part: Mapped[str] = mapped_column("spare_part", String)
    labor_hours: Mapped[float] = mapped_column("labor_hours")
    rate: Mapped[float] = mapped_column("rate")

    __mapper_args__ = {"polymorphic_identity": "workshop"}


class POSLine(InvoiceLine):
    """POS-generated line item model."""

    __tablename__ = "pos_invoice_lines"

    id: Mapped[_uuid.UUID] = mapped_column(
        TENANT_UUID, ForeignKey("invoice_lines.id"), primary_key=True
    )
    pos_receipt_line_id: Mapped[_uuid.UUID | None] = mapped_column(
        "pos_receipt_line_id", TENANT_UUID, nullable=True
    )

    __mapper_args__ = {"polymorphic_identity": "pos"}
