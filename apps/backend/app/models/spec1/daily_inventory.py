"""
Daily Inventory Model - Inventario diario por producto
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, LargeBinary, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.models.spec1.sqltypes import GUID


class DailyInventory(Base):
    """Inventario diario por producto y fecha"""
    __tablename__ = "daily_inventory"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tenants.id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    
    stock_inicial: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    venta_unidades: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    stock_final: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    ajuste: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    
    precio_unitario_venta: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)
    importe_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4), nullable=True)
    
    # Trazabilidad de importación
    source_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    import_digest: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    
    created_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)

    def __repr__(self):
        return f"<DailyInventory {self.fecha} - Product {self.product_id}>"
