# Company User model
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import IS_SQLITE, Base

UUID = PGUUID(as_uuid=True)
TENANT_UUID = UUID.with_variant(String(36), "sqlite")

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class CompanyUser(Base):
    __tablename__ = "company_users"
    __table_args__ = (
        sa.UniqueConstraint("tenant_id", "email", name="uq_company_user_tenant_email"),
        sa.UniqueConstraint("tenant_id", "username", name="uq_company_user_tenant_username"),
        {"extend_existing": True},
    )

    # PK UUID
    id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID,
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()") if not IS_SQLITE else None,
        nullable=False,
        index=True,
    )

    # FK -> tenants.id (UUID)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        TENANT_UUID,
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(254), nullable=False)
    username: Mapped[str] = mapped_column(sa.String(100), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    is_company_admin: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    password_hash: Mapped[str] = mapped_column(sa.String, nullable=False)
    password_token_created: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    is_verified: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant")

    # Audit
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
    def is_superuser(self) -> bool:
        """Check if user is superuser."""
        return self.is_company_admin

    @property
    def is_staff(self) -> bool:
        """Check if user is staff."""
        return self.is_company_admin
