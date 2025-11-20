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
    usuario_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_users.id"),
    )
    rol_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_roles.id"),
    )
    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=True
    )

    # Relaciones opcionales (puedes activarlas si las necesitas)
    usuario = relationship("CompanyUser", foreign_keys=[usuario_id], backref="assigned_roles")
    assigned_by = relationship("CompanyUser", foreign_keys=[assigned_by_id])
    role: Mapped["CompanyRole"] = relationship()
    tenant = relationship("Tenant", foreign_keys=[tenant_id])

    def __repr__(self):
        """Function __repr__ - auto-generated docstring."""
        return f"<CompanyUserRole usuario_id={self.usuario_id} rol_id={self.rol_id}>"

    # Aliases for compatibility
    @property
    def user_id(self) -> UUID:
        """Alias for usuario_id."""
        return self.usuario_id

    @user_id.setter
    def user_id(self, value: UUID) -> None:
        """Setter for user_id."""
        self.usuario_id = value

    @property
    def role_id(self) -> UUID:
        """Alias for rol_id."""
        return self.rol_id

    @role_id.setter
    def role_id(self, value: UUID) -> None:
        """Setter for role_id."""
        self.rol_id = value

    @property
    def active(self) -> bool:
        """Alias for activo."""
        return self.activo

    @active.setter
    def active(self, value: bool) -> None:
        """Setter for active."""
        self.activo = value


# Keep old name for backward compatibility during migration
UsuarioRolEmpresa = CompanyUserRole
