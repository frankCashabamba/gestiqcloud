"""Module: rolempresas.py

Auto-generated module docstring."""

from typing import Optional
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import (JSON, Boolean, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.empresa import Empresa, RolBase


class RolEmpresa(Base):
    """ Class RolEmpresa - auto-generated docstring. """
    __tablename__ = "core_rolempresa"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"))
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    permisos: Mapped[dict] = mapped_column(
    MutableDict.as_mutable(JSON),
    nullable=False,
    default=dict,
)
    rol_base_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core_rolbase.id"), nullable=True)
    creado_por_empresa: Mapped[bool] = mapped_column(Boolean, default=False)

    empresa: Mapped[Empresa] = relationship(Empresa)
    rol_base: Mapped[Optional["RolBase"]] = relationship("RolBase")

    __table_args__ = (UniqueConstraint("empresa_id", "nombre", name="uq_empresa_rol"),)
