"""Company Role models"""

from typing import Optional
from uuid import UUID, uuid4

from app.config.database import Base
from app.models.company.company import RolBase
from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID_TYPE = PGUUID(as_uuid=True)
TENANT_UUID = UUID_TYPE.with_variant(String(36), "sqlite")


class CompanyRole(Base):
    """Company Role model."""

    __tablename__ = "company_roles"

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=True
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
        UniqueConstraint("tenant_id", "name", name="uq_company_role"),
        {"extend_existing": True},
    )
