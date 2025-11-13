"""Modelos POS: Vales/Store Credit"""

import uuid
from datetime import date, datetime

from app.config.database import Base
from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class StoreCredit(Base):
    """Vale/Crédito de tienda"""

    __tablename__ = "store_credits"
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
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_initial: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_remaining: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        # active, redeemed, expired, void
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    customer = relationship("Cliente", foreign_keys=[customer_id])
    events: Mapped[list["StoreCreditEvent"]] = relationship(
        "StoreCreditEvent", back_populates="credit", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<StoreCredit {self.code} - {self.amount_remaining}/{self.amount_initial}>"


class StoreCreditEvent(Base):
    """Evento de vale (emisión, uso, expiración)"""

    __tablename__ = "store_credit_events"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    credit_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("store_credits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        # issue, redeem, expire, void
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ref_doc_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_doc_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    credit: Mapped["StoreCredit"] = relationship("StoreCredit", back_populates="events")

    def __repr__(self):
        return f"<StoreCreditEvent {self.type} - {self.amount}>"
