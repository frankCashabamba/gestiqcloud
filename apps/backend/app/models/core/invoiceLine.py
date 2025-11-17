"""Module: invoiceLine.py - Invoice line item models."""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class LineaFactura(Base):
    """Invoice line item base model."""

    __tablename__ = "invoice_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4(),
    )
    invoice_id: Mapped[UUID] = mapped_column(
        "invoice_id", PGUUID(as_uuid=True), ForeignKey("invoices.id")
    )
    sector: Mapped[str] = mapped_column("sector", String(50))
    description: Mapped[str] = mapped_column("description", String)
    quantity: Mapped[float] = mapped_column("quantity")
    unit_price: Mapped[float] = mapped_column("unit_price")
    vat: Mapped[float] = mapped_column("vat", default=0)

    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": sector}


class BakeryLine(LineaFactura):
    """Bakery line item model."""

    __tablename__ = "bakery_lines"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )
    bread_type: Mapped[str] = mapped_column("bread_type", String)
    grams: Mapped[float] = mapped_column("grams")

    __mapper_args__ = {"polymorphic_identity": "bakery"}


class WorkshopLine(LineaFactura):
    """Workshop line item model."""

    __tablename__ = "workshop_lines"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("invoice_lines.id"), primary_key=True
    )
    spare_part: Mapped[str] = mapped_column("spare_part", String)
    labor_hours: Mapped[float] = mapped_column("labor_hours")
    rate: Mapped[float] = mapped_column("rate")

    __mapper_args__ = {"polymorphic_identity": "workshop"}
