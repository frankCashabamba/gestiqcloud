"""Purchase Models"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Purchase(Base):
    """Purchase Order"""

    __tablename__ = "purchases"
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
    number: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False, default=date.today)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    taxes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        # draft, ordered, received, invoiced, cancelled
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    lines: Mapped[list["PurchaseLine"]] = relationship(
        "PurchaseLine", back_populates="purchase", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Purchase {self.number} - {self.total}>"


class PurchaseLine(Base):
    """Purchase Order Line"""

    __tablename__ = "purchase_lines"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    purchase_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="lines")
    product = relationship("Product", foreign_keys=[product_id])

    def __repr__(self):
        return f"<PurchaseLine {self.description} - {self.quantity}>"
