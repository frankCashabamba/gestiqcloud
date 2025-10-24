"""
Purchase Model - Compras a proveedores
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.models.spec1.sqltypes import GUID


class Purchase(Base):
    """Compras a proveedores"""
    __tablename__ = "purchase"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tenants.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    
    supplier_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    total: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 4), nullable=True)
    
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Trazabilidad de importación
    source_file: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)

    def __repr__(self):
        return f"<Purchase {self.fecha} - {self.supplier_name}>"
