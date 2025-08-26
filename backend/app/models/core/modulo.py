"""Module: modulo.py

Auto-generated module docstring."""
# pylint: disable=unsubscriptable-object
from datetime import datetime
from typing import  Optional

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.empresa import Empresa

class Modulo(Base):
    """ Class Modulo - auto-generated docstring. """
    __tablename__ = "modulos_modulo"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)# type: ignore
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)# type: ignore
    descripcion: Mapped[Optional[str]] = mapped_column(Text)# type: ignore
    activo: Mapped[bool] = mapped_column(Boolean, default=True)# type: ignore
    icono: Mapped[Optional[str]] = mapped_column(String(100), default="📦")# type: ignore
    url: Mapped[Optional[str]] = mapped_column(String(255))# type: ignore
    plantilla_inicial: Mapped[str] = mapped_column(String(255), nullable=False)# type: ignore
    context_type: Mapped[str] = mapped_column(String(10), default="none")# type: ignore
    modelo_objetivo: Mapped[Optional[str]] = mapped_column(String(255))# type: ignore
    filtros_contexto: Mapped[Optional[dict]] = mapped_column(JSONB)# type: ignore
    categoria: Mapped[Optional[str]] = mapped_column(String(50))# type: ignore

class EmpresaModulo(Base):
    """ Class EmpresaModulo - auto-generated docstring. """
    __tablename__ = "modulos_empresamodulo"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)  # type: ignore
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), nullable=False) # type: ignore
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos_modulo.id"), nullable=False) # type: ignore
    activo: Mapped[bool] = mapped_column(Boolean, default=True) # type: ignore
    fecha_activacion: Mapped[datetime] = mapped_column(Date, default=datetime.utcnow) # type: ignore
    fecha_expiracion: Mapped[Optional[datetime]] = mapped_column(Date) # type: ignore
    plantilla_inicial: Mapped[Optional[str]] = mapped_column(String(255)) # type: ignore

    modulo: Mapped["Modulo"] = relationship("Modulo") # type: ignore
    empresa: Mapped[Empresa] = relationship(Empresa) # type: ignore

    __table_args__ = (
        UniqueConstraint("empresa_id", "modulo_id", name="modulos_empresamodulo_empresa_id_modulo_id_uniq"),
    )


class ModuloAsignado(Base):
    """ Class ModuloAsignado - auto-generated docstring. """
    __tablename__ = "modulos_moduloasignado"
    
    id: Mapped[int] = mapped_column(primary_key=True)  # pylint: disable=unsubscriptable-object
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), nullable=False) # type: ignore
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios_usuarioempresa.id"), nullable=False) # type: ignore
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos_modulo.id"), nullable=False) # type: ignore
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow) # type: ignore
    ver_modulo_auto: Mapped[bool] = mapped_column(Boolean, default=True) # type: ignore
    modulo: Mapped["Modulo"] = relationship("Modulo", lazy="joined")  # 👈  # type: ignore

    __table_args__ = (
        UniqueConstraint("usuario_id", "modulo_id", "empresa_id", name="modulos_moduloasignado_usuario_id_modulo_id_empresa_id_uniq"),
    )
