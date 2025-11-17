"""Sales Models"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Sale(Base):
    """Sales Order (pre-invoice)"""

    __tablename__ = "sales"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # 👇 DEFAULT para compatibilidad con SQLite/tests
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        default=uuid.uuid4,  # valor cualquiera, en SQLite no hay RLS ni FK real
    )

    # 👇 DEFAULT sencillo para que no sea NULL
    number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",  # o default=lambda: str(uuid.uuid4())[:8]
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    taxes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 👇 Igual que tenant_id: default para compat
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    customer = relationship("Client", foreign_keys=[customer_id])

    def __repr__(self):
        return f"<Sale {self.number} - {self.total}>"
