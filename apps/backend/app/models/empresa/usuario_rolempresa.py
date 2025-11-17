"""Module: usuario_rolempresa.py

Auto-generated module docstring."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.rolempresas import RolEmpresa


class UsuarioRolempresa(Base):
    """Class UsuarioRolempresa - auto-generated docstring."""

    __tablename__ = "usuarios_usuariorolempresa"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("usuarios_usuarioempresa.id"),
    )
    rol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("core_rolempresa.id"),
    )
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    fecha_asignacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    asignado_por_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("usuarios_usuarioempresa.id"), nullable=True
    )

    # Relaciones opcionales (puedes activarlas si las necesitas)
    usuario = relationship("UsuarioEmpresa", foreign_keys=[usuario_id], backref="roles_asignados")
    asignado_por = relationship("UsuarioEmpresa", foreign_keys=[asignado_por_id])
    rol: Mapped["RolEmpresa"] = relationship()
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        """Function __repr__ - auto-generated docstring."""
        return f"<UsuarioRolempresa usuario_id={self.usuario_id} rol_id={self.rol_id}>"
