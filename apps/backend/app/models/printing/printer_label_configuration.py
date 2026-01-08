from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class PrinterLabelConfiguration(Base):
    __tablename__ = "printer_label_configurations"
    __table_args__ = {"extend_existing": True}

    id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    tenant_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
        index=True,
    )
    printer_port: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    width_mm: Mapped[float | None] = mapped_column(Float)
    height_mm: Mapped[float | None] = mapped_column(Float)
    gap_mm: Mapped[float | None] = mapped_column(Float)
    columns: Mapped[int | None] = mapped_column(Integer)
    column_gap_mm: Mapped[float | None] = mapped_column(Float)
    copies: Mapped[int | None] = mapped_column(Integer)
    show_price: Mapped[bool | None] = mapped_column(Boolean)
    show_category: Mapped[bool | None] = mapped_column(Boolean)
    header_text: Mapped[str | None] = mapped_column(String(60))
    footer_text: Mapped[str | None] = mapped_column(String(60))
    offset_xmm: Mapped[float | None] = mapped_column(Float)
    offset_ymm: Mapped[float | None] = mapped_column(Float)
    barcode_width: Mapped[float | None] = mapped_column(Float)
    price_alignment: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
