"""Module: settings.py

Auto-generated module docstring."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (JSON, Boolean, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.empresa import Empresa, Idioma, Moneda

class ConfiguracionEmpresa(Base):
    """ Class ConfiguracionEmpresa - auto-generated docstring. """
    __tablename__ = "core_configuracionempresa"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), unique=True, nullable=False)

    idioma_predeterminado: Mapped[str] = mapped_column(String(10), default="es")
    zona_horaria: Mapped[str] = mapped_column(String(50), default="UTC")
    moneda: Mapped[str] = mapped_column(String(10), default="USD")

    logo_empresa: Mapped[Optional[str]] = mapped_column(String(100))
    color_secundario: Mapped[str] = mapped_column(String(7), default="#6c757d")
    color_primario: Mapped[str] = mapped_column(String(7), default="#4f46e5")

    permitir_roles_personalizados: Mapped[bool] = mapped_column(Boolean, default=True)
    limite_usuarios: Mapped[int] = mapped_column(Integer, default=10)

    dias_laborales: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["lunes", "martes", "miércoles", "jueves", "viernes"])
    horario_atencion: Mapped[Dict[str, str]] = mapped_column(JSON, default=lambda: {"inicio": "09:00", "fin": "18:00"})
    tipo_operacion: Mapped[str] = mapped_column(String, default="ventas")

    razon_social: Mapped[Optional[str]] = mapped_column(String)
    rfc: Mapped[Optional[str]] = mapped_column(String)
    regimen_fiscal: Mapped[Optional[str]] = mapped_column(String)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    idioma_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core_idioma.id"))
    moneda_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core_moneda.id"))

    empresa: Mapped[Empresa] = relationship(Empresa)



class ConfiguracionInventarioEmpresa(Base):
    """ Class ConfiguracionInventarioEmpresa - auto-generated docstring. """
    __tablename__ = "core_configuracioninventarioempresa"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("core_empresa.id"), unique=True, nullable=False)

    control_stock_activo: Mapped[bool] = mapped_column(Boolean, default=True)
    notificar_bajo_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_minimo_global: Mapped[Optional[int]] = mapped_column(Integer)

    um_predeterminadas: Mapped[Optional[dict]] = mapped_column(JSON)
    categorias_personalizadas: Mapped[bool] = mapped_column(Boolean, default=False)
    campos_extra_producto: Mapped[Optional[dict]] = mapped_column(JSON)

    empresa: Mapped[Empresa] = relationship(Empresa)
