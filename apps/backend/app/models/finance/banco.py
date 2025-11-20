"""Bank Models"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class BankMovement(Base):
    """Bank Movement"""

    __tablename__ = "bank_movements"
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
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        # FK a bank_accounts cuando se cree esa tabla
    )
    date: Mapped[date] = mapped_column(Date(), nullable=False, default=date.today, index=True)
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        # income, expense
    )
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    previous_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    new_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    bank_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        return f"<BankMovement {self.type} - {self.amount}>"
