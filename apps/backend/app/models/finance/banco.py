"""Modelo de Banco"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, String, Numeric, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class BancoMovimiento(Base):
    """Movimiento bancario"""

    __tablename__ = "banco_movimientos"
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
    cuenta_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        # FK a bank_accounts cuando se cree esa tabla
    )
    fecha: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today, index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        # ingreso, egreso
    )
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    importe: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    saldo_anterior: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    saldo_nuevo: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    ref_bancaria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    conciliado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        return f"<BancoMovimiento {self.tipo} - {self.importe}>"
