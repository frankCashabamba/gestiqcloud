"""
Sale Models - Documentos de venta simplificados
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class SaleHeader(Base):
    """Cabecera de venta"""
    __tablename__ = "sale_header"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False, default="Consumidor Final")
    
    total: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, default=0)
    total_tax: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, default=0)
    payment_method: Mapped[str] = mapped_column(Text, nullable=False, default="Efectivo")
    
    sale_uuid: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    pos_receipt_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    created_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # Relationship
    lines: Mapped[list["SaleLine"]] = relationship(back_populates="sale", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SaleHeader {self.fecha} - Total {self.total}>"


class SaleLine(Base):
    """Línea de venta"""
    __tablename__ = "sale_line"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sale_header.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    
    qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    tax_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=0)
    total_line: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    
    created_at: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Relationship
    sale: Mapped["SaleHeader"] = relationship(back_populates="lines")

    def __repr__(self):
        return f"<SaleLine Product {self.product_id} - Qty {self.qty}>"
