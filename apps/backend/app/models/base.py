"""
Base models for common patterns in the application.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, String, Text, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

UUID_TYPE = PGUUID(as_uuid=True)
TENANT_UUID = UUID_TYPE.with_variant(String(36), "sqlite")


def _get_now():
    """Get current UTC datetime for Python-side defaults."""
    return datetime.now(UTC)


class BaseCatalogModel(Base):
    """
    Base model for catalog-like entities with common fields.

    This model provides standard fields for entities that behave as catalogs:
    - UUID primary key with tenant isolation
    - Optional code field for external identifiers
    - Required name field
    - Optional description
    - Active/inactive status with backward compatibility
    - Automatic timestamps

    Models that inherit from this should define:
    - __tablename__
    - Any additional specific fields
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )

    
    # Backward compatibility alias for active -> is_active
    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value


class BaseCatalogModelWithoutTenant(Base):
    """
    Base model for system-wide catalogs (no tenant isolation).

    Used for entities that are shared across all tenants like:
    - System reference data
    - Global configurations
    - Core catalogs
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )

    # Backward compatibility alias for active -> is_active
    @hybrid_property
    def active(self) -> bool:
        return self.is_active

    @active.setter
    def active(self, value: bool) -> None:
        self.is_active = value


class BaseTransactionalModel(Base):
    """
    Base model for transactional entities (not catalogs).

    Used for entities that represent business transactions, operations, or events:
    - Sales orders, invoices, payments
    - Production orders, inventory movements
    - User activities, logs

    Provides:
    - UUID primary key with tenant isolation
    - Automatic timestamps
    - No catalog-specific fields (code, name, is_active)
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )


class BaseTransactionalModelWithoutTenant(Base):
    """
    Base model for system-wide transactional entities (no tenant isolation).

    Used for system-level transactions that affect all tenants:
    - System logs, audits
    - Global events
    - System configurations changes
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(TENANT_UUID, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=_get_now, server_default=func.now(), onupdate=_get_now, nullable=False
    )
