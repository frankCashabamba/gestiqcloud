"""Module: rolempresas.py

Auto-generated module docstring."""

from typing import Optional
from uuid import UUID, uuid4

from app.config.database import Base
from app.models.empresa.empresa import RolBase
from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship


class RolEmpresa(Base):
    """Class RolEmpresa - auto-generated docstring."""

    __tablename__ = "core_rolempresa"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    permisos: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
    )
    rol_base_id: Mapped[UUID | None] = mapped_column(ForeignKey("core_rolbase.id"), nullable=True)
    creado_por_empresa: Mapped[bool] = mapped_column(Boolean, default=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    rol_base: Mapped[Optional["RolBase"]] = relationship("RolBase")

    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_empresa_rol"),
        {"extend_existing": True},
    )
