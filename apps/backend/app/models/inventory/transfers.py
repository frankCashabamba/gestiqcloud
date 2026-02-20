from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SQLEnum
from sqlalchemy import String, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


def _uuid_col():
    try:
        return PGUUID(as_uuid=True)
    except Exception:
        return String


class TransferStatus(str, Enum):
    """Estados posibles de una transferencia de stock"""

    DRAFT = "draft"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StockTransfer(Base):
    """Transferencia de stock entre almacenes"""

    __tablename__ = "stock_transfers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        _uuid_col(),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=sa_text("gen_random_uuid()"),
    )
    tenant_id: Mapped[str] = mapped_column(_uuid_col(), index=True, nullable=False)
    from_warehouse_id: Mapped[str] = mapped_column(
        _uuid_col(), index=True, nullable=False
    )
    to_warehouse_id: Mapped[str] = mapped_column(
        _uuid_col(), index=True, nullable=False
    )
    product_id: Mapped[str] = mapped_column(_uuid_col(), index=True, nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        SQLEnum(TransferStatus),
        default=TransferStatus.DRAFT,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=sa_text("now()"),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
