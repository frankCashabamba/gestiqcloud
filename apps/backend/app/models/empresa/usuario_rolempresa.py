"""Module: usuario_rolempresa.py

Auto-generated module docstring."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.empresa import Empresa, UsuarioEmpresa
from app.models.empresa.rolempresas import RolEmpresa


class UsuarioRolempresa(Base):
    """ Class UsuarioRolempresa - auto-generated docstring. """
    __tablename__ = "usuarios_usuariorolempresa"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"))
    rol_id: Mapped[int] = mapped_column(ForeignKey("core_rolempresa.id"))
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    asignado_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"), nullable=True)

    # Relaciones opcionales (puedes activarlas si las necesitas)
    usuario: Mapped["UsuarioEmpresa"] = relationship(foreign_keys=[usuario_id], backref="roles_asignados")
    asignado_por: Mapped[Optional["UsuarioEmpresa"]] = relationship(foreign_keys=[asignado_por_id])
    rol: Mapped["RolEmpresa"] = relationship()
    empresa: Mapped["Empresa"] = relationship()

    def __repr__(self):
        """ Function __repr__ - auto-generated docstring. """
        return f"<UsuarioRolempresa usuario_id={self.usuario_id} rol_id={self.rol_id}>"
