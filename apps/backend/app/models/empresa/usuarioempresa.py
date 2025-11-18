# app/models/usuarioempresa.py
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import IS_SQLITE, Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class CompanyUser(Base):
    __tablename__ = "company_users"
    __table_args__ = (
        # Unicidad por tenant (elige esto o uniques globales en columnas)
        sa.UniqueConstraint("tenant_id", "email", name="uq_company_user_tenant_email"),
        sa.UniqueConstraint("tenant_id", "username", name="uq_company_user_tenant_username"),
        {"extend_existing": True},
    )

    # PK UUID
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Genera UUID en Python antes de INSERT
        server_default=sa.text("gen_random_uuid()") if not IS_SQLITE else None,
        nullable=False,
        index=True,
    )

    # FK -> tenants.id (UUID)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        sa.String(254), nullable=False
    )  # considera CITEXT si quieres case-insensitive
    username: Mapped[str] = mapped_column(sa.String(100), nullable=False)

    active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("true"))
    is_admin: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    password_hash: Mapped[str] = mapped_column(sa.String, nullable=False)
    password_token_created: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    # Relación
    tenant: Mapped["Tenant"] = relationship("Tenant")  # o back_populates si defines el lado inverso

    # Auditoría
    failed_login_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_password_change_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.text("CURRENT_TIMESTAMP"),
    )

    def __repr__(self) -> str:
        return f"<CompanyUser email={self.email}>"

    @property
    def is_active(self) -> bool:
        """Function is_active - auto-generated docstring."""
        return self.active

    @property
    def is_superuser(self) -> bool:
        """Function is_superuser - auto-generated docstring."""
        return self.is_admin

    @property
    def is_staff(self) -> bool:
        """Function is_staff - auto-generated docstring."""
        return self.is_admin


# Keep old name for backward compatibility during migration
UsuarioEmpresa = CompanyUser
