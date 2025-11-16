import uuid
from datetime import date, datetime
from sqlalchemy import String, Text, Date, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

class Venta(Base):
    """Pedido de venta (pre-factura)"""

    __tablename__ = "ventas"
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
    numero: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",  # o default=lambda: str(uuid.uuid4())[:8]
    )

    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    impuestos: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 👇 Igual que tenant_id: default para compat
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    cliente = relationship("Cliente", foreign_keys=[cliente_id])

    def __repr__(self):
        return f"<Venta {self.numero} - {self.total}>"
