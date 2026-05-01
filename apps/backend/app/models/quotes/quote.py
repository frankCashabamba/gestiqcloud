"""Quote (presupuesto) model.

A Quote is a commercial proposal that may be later approved and converted into
a SalesOrder. Lines are stored as a JSONB list to keep the schema lean.

Lifecycle (status):
    DRAFT      → editable, can be approved or deleted.
    APPROVED   → no longer editable; eligible for conversion.
    CONVERTED  → already turned into a SalesOrder (see ``converted_to_order_id``).
    REJECTED   → manually closed without conversion.
    EXPIRED    → past its valid_until date.
    CANCELLED  → withdrawn by the seller.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_UUID, BaseTransactionalModel


class QuoteStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    CONVERTED = "CONVERTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Quote(BaseTransactionalModel):
    __tablename__ = "quotes"
    __table_args__ = {"extend_existing": True}

    number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(TENANT_UUID, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=QuoteStatus.DRAFT.value, index=True
    )

    # Lines: list[{product_id, name, qty, unit_price, tax_rate, discount_percent, line_total}]
    lines: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Totals
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Dates
    quote_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Misc
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_to_order_id: Mapped[uuid.UUID | None] = mapped_column(
        TENANT_UUID, nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(TENANT_UUID, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
