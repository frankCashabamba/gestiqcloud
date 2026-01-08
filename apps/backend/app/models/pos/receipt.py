"""POS Models: Receipts and Payments"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class POSReceipt(Base):
    """POS sales receipt"""

    __tablename__ = "pos_receipts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    register_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pos_registers.id"), nullable=False, index=True
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pos_shifts.id"), nullable=False, index=True
    )
    cashier_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        # draft, paid, voided, invoiced
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
    )
    gross_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    register = relationship("POSRegister")
    shift: Mapped["POSShift"] = relationship("POSShift", back_populates="receipts")  # noqa: F821
    cashier = relationship("CompanyUser", foreign_keys=[cashier_id])
    customer = relationship("Client", foreign_keys=[customer_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    lines: Mapped[list["POSReceiptLine"]] = relationship(
        "POSReceiptLine", back_populates="receipt", cascade="all, delete-orphan"
    )
    payments: Mapped[list["POSPayment"]] = relationship(
        "POSPayment", back_populates="receipt", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<POSReceipt {self.number} - {self.gross_total}>"


class POSReceiptLine(Base):
    """Receipt line"""

    __tablename__ = "pos_receipt_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pos_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(20), nullable=False, default="unit")
    unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    line_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    net_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cogs_unit: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    cogs_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gross_profit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gross_margin_pct: Mapped[float] = mapped_column(
        Numeric(7, 4), nullable=False, default=0
    )

    # Relationships
    receipt: Mapped["POSReceipt"] = relationship("POSReceipt", back_populates="lines")
    product = relationship("Product")

    def __repr__(self):
        return f"<POSReceiptLine {self.product_id} x {self.qty}>"


class POSPayment(Base):
    """Receipt payment"""

    __tablename__ = "pos_payments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    receipt_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pos_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        # cash, card, store_credit, link
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    receipt: Mapped["POSReceipt"] = relationship("POSReceipt", back_populates="payments")

    def __repr__(self):
        return f"<POSPayment {self.method} - {self.amount}>"
