"""Module: usuario_rolempresa.py

Auto-generated module docstring."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.empresa.rolempresas import CompanyRole


class CompanyUserRole(Base):
    """Class CompanyUserRole - auto-generated docstring."""

    __tablename__ = "company_user_roles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_users.id"),
    )
    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_roles.id"),
    )
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=True
    )

    # Relaciones opcionales (puedes activarlas si las necesitas)
    user = relationship("CompanyUser", foreign_keys=[user_id], backref="assigned_roles")
    assigned_by = relationship("CompanyUser", foreign_keys=[assigned_by_id])
    role: Mapped["CompanyRole"] = relationship()
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        """Function __repr__ - auto-generated docstring."""
        return f"<CompanyUserRole user_id={self.user_id} role_id={self.role_id}>"
