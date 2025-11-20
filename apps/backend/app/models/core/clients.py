"""Module: clients.py

Auto-generated module docstring."""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Client(Base):
    """Class Client - auto-generated docstring."""

    __tablename__ = "clients"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=lambda: __import__("uuid").uuid4(),
        index=True,
    )
    name: Mapped[str] = mapped_column("name", String, nullable=False)
    tax_id: Mapped[str] = mapped_column("tax_id", String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column("phone", String, nullable=True)
    address: Mapped[str] = mapped_column("address", String, nullable=True)
    city: Mapped[str] = mapped_column("city", String, nullable=True)
    state: Mapped[str] = mapped_column("state", String, nullable=True)
    country: Mapped[str] = mapped_column("country", String, nullable=True)
    postal_code: Mapped[str] = mapped_column("postal_code", String, nullable=True)

    tenant_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=True
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])


# Keep old name for backward compatibility during migration
Cliente = Client
