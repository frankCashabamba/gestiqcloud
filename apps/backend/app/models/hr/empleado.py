"""Modelos de RRHH"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.auth.useradmis import SuperUser


class Empleado(Base):
    """Empleado"""

    __tablename__ = "empleados"
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
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("auth_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    codigo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellidos: Mapped[str | None] = mapped_column(String(255), nullable=True)
    documento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_alta: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    fecha_baja: Mapped[date | None] = mapped_column(Date, nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salario_base: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    # Vincular al modelo de usuario administrativo correcto
    usuario = relationship(SuperUser, foreign_keys=[usuario_id])
    vacaciones: Mapped[list["Vacacion"]] = relationship(
        "Vacacion", back_populates="empleado", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Empleado {self.name} {self.apellidos}>"


class Vacacion(Base):
    """Solicitud de vacaciones"""

    __tablename__ = "vacaciones"
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
    empleado_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("empleados.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    dias: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="solicitada",
        index=True,
        # solicitada, aprobada, rechazada
    )
    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    notas: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    empleado: Mapped["Empleado"] = relationship("Empleado", back_populates="vacaciones")

    def __repr__(self):
        return f"<Vacacion {self.empleado_id} - {self.dias} días>"
