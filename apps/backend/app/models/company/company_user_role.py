"""Company User Role models"""

from datetime import datetime
from uuid import UUID

from app.config.database import Base
from app.models.company.company_role import CompanyRole
from sqlalchemy import Boolean, DateTime, ForeignKey, text, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

UUID_TYPE = PGUUID(as_uuid=True)
TENANT_UUID = UUID_TYPE.with_variant(String(36), "sqlite")

class CompanyUserRole(Base):
    """Company User Role model."""

    __tablename__ = "company_user_roles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        "usuario_id",
        TENANT_UUID,
        ForeignKey("company_users.id"),
    )
    role_id: Mapped[UUID] = mapped_column(
        "rol_id",
        TENANT_UUID,
        ForeignKey("company_roles.id"),
    )
    tenant_id: Mapped[UUID | None] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        TENANT_UUID, ForeignKey("company_users.id"), nullable=True
    )

    # Relationships
    user = relationship("CompanyUser", foreign_keys=[user_id], backref="assigned_roles")
    assigned_by = relationship("CompanyUser", foreign_keys=[assigned_by_id])
    role: Mapped["CompanyRole"] = relationship()
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        """Return user role representation."""
        return f"<CompanyUserRole user_id={self.user_id} role_id={self.role_id}>"

    # Aliases for compatibility
    @property
    def active(self) -> bool:
        """Alias for is_active."""
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value

    # Backward-compatible aliases (legacy field names)
    @property
    def rol_id(self):
        return self.role_id

    @rol_id.setter
    def rol_id(self, value):
        self.role_id = value

    @property
    def usuario_id(self):
        return self.user_id

    @usuario_id.setter
    def usuario_id(self, value):
        self.user_id = value

    @property
    def activo(self):
        return self.is_active

    @activo.setter
    def activo(self, value):
        self.is_active = value
