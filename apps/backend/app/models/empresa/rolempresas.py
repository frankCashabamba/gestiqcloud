"""Module: rolempresas.py

Auto-generated module docstring."""

from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.empresa import RolBase


class CompanyRole(Base):
    """Class CompanyRole - auto-generated docstring."""

    __tablename__ = "company_roles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
    )
    base_role_id: Mapped[UUID | None] = mapped_column(ForeignKey("base_roles.id"), nullable=True)
    created_by_company: Mapped[bool] = mapped_column(Boolean, default=False)

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    base_role: Mapped[Optional["RolBase"]] = relationship("RolBase")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_empresa_rol"),
        {"extend_existing": True},
    )


# Keep old name for backward compatibility during migration
RolEmpresa = CompanyRole
