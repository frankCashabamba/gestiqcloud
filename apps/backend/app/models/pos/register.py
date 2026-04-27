"""Modelos POS: Registros y Turnos"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.base import BaseTransactionalModel

UUID_TYPE = PGUUID(as_uuid=True)
TENANT_UUID = UUID_TYPE.with_variant(String(36), "sqlite")


class POSRegister(BaseTransactionalModel):
    """Registro/Caja de punto de venta"""

    __tablename__ = "pos_registers"
    __table_args__ = {"extend_existing": True}

    # Additional fields specific to POSRegister
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        TENANT_UUID,
        nullable=True,
        # Para futuro multi-tienda
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys="[POSRegister.tenant_id]")
    shifts: Mapped[list["POSShift"]] = relationship(
        "POSShift", back_populates="register", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<POSRegister {self.name}>"


class POSShift(Base):
    """Turno de caja"""

    __tablename__ = "pos_shifts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID, primary_key=True, default=uuid.uuid4, index=True
    )
    register_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID,
        ForeignKey("pos_registers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(TENANT_UUID, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(UTC))
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    opening_float: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    closing_total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        # open, closed
    )

    # Relationships
    register: Mapped["POSRegister"] = relationship("POSRegister", back_populates="shifts")
    receipts: Mapped[list["POSReceipt"]] = relationship(  # noqa: F821
        "POSReceipt", back_populates="shift", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<POSShift {self.id} - {self.status}>"
