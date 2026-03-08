"""Module: clients.py

Auto-generated module docstring."""

import uuid as _uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.tenant import TENANT_UUID


class Client(Base):
    """Class Client - auto-generated docstring."""

    __tablename__ = "clients"
    __table_args__ = {"extend_existing": True}

    id: Mapped[_uuid.UUID] = mapped_column(
        TENANT_UUID,
        primary_key=True,
        default=_uuid.uuid4,
        index=True,
    )
    name: Mapped[str] = mapped_column("name", String, nullable=False)
    tax_id: Mapped[str] = mapped_column("tax_id", String, nullable=True)
    tax_id_type: Mapped[str] = mapped_column("tax_id_type", String(30), nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column("phone", String, nullable=True)
    address: Mapped[str] = mapped_column("address", String, nullable=True)
    city: Mapped[str] = mapped_column("city", String, nullable=True)
    state: Mapped[str] = mapped_column("state", String, nullable=True)
    country: Mapped[str] = mapped_column("country", String, nullable=True)
    postal_code: Mapped[str] = mapped_column("postal_code", String, nullable=True)
    is_wholesale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    tenant_id: Mapped[_uuid.UUID | None] = mapped_column(
        TENANT_UUID, ForeignKey("tenants.id"), index=True, nullable=True
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])


# Keep old name for backward compatibility during migration
Cliente = Client
