"""
Production Order Model - Órdenes de producción
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ProductionOrder(Base):
    """Orden de producción"""
    __tablename__ = "production_order"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    product_fg_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    
    qty_plan: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    qty_real: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="PLANIFICADA")
    merma_real: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 3), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ProductionOrder {self.fecha} - Product {self.product_fg_id} - {self.estado}>"
