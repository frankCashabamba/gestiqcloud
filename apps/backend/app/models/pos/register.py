"""Modelos POS: Registros y Turnos"""

import uuid
from datetime import datetime

from app.config.database import Base
from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class POSRegister(Base):
    """Registro/Caja de punto de venta"""

    __tablename__ = "pos_registers"
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
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        # Para futuro multi-tienda
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
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
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    register_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pos_registers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
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
