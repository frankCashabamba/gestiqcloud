"""
Modelos base para líneas de documentos.

Define una jerarquía común para todas las líneas de documentos comerciales:
- Facturas (invoice_lines)
- Órdenes de venta (sales_order_items) 
- Recibos POS (pos_receipt_lines)
- Órdenes de compra (purchase_order_lines)

Esto permite:
- Reutilización de código
- Consistencia en la estructura
- Facilita conversiones entre documentos
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import String, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class DocumentLineBase:
    """
    Clase base abstracta (mixin) para todas las líneas de documento.
    
    Define los campos comunes que toda línea de documento debe tener.
    No se mapea a una tabla, solo provee estructura común.
    """
    
    # Campos comunes a todas las líneas
    product_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True), 
        nullable=True,
        comment="Producto (puede ser nulo para líneas de texto libre)"
    )
    
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Descripción del item/servicio"
    )
    
    qty: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        comment="Cantidad"
    )
    
    unit_price: Mapped[float] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        default=0,
        comment="Precio unitario antes de impuestos"
    )
    
    tax_rate: Mapped[float] = mapped_column(
        Numeric(6, 4),
        nullable=False,
        default=0,
        comment="Tasa de impuesto (0.21 = 21%)"
    )
    
    discount_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        comment="Porcentaje de descuento (10 = 10%)"
    )
    
    @property
    def subtotal(self) -> float:
        """Subtotal antes de descuentos e impuestos"""
        return float(self.qty * self.unit_price)
    
    @property
    def discount_amount(self) -> float:
        """Monto del descuento"""
        return float(self.subtotal * (self.discount_pct / 100))
    
    @property
    def base_amount(self) -> float:
        """Base imponible (después de descuento, antes de impuestos)"""
        return float(self.subtotal - self.discount_amount)
    
    @property
    def tax_amount(self) -> float:
        """Monto del impuesto"""
        return float(self.base_amount * self.tax_rate)
    
    @property
    def total(self) -> float:
        """Total de la línea (base + impuestos)"""
        return float(self.base_amount + self.tax_amount)


# NOTA: Los modelos existentes deben migrar gradualmente a usar este mixin
# 
# Ejemplo de uso:
# 
# class InvoiceLine(DocumentLineBase, Base):
#     __tablename__ = "invoice_lines"
#     
#     id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
#     invoice_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True), 
#         ForeignKey("invoices.id")
#     )
#     # Campos específicos de factura
#     sector: Mapped[Optional[str]] = mapped_column(String(50))
#
# class SalesOrderItem(DocumentLineBase, Base):
#     __tablename__ = "sales_order_items"
#     
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     order_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales_orders.id"))
#     # Campos específicos de orden de venta
#
# class POSReceiptLine(DocumentLineBase, Base):
#     __tablename__ = "pos_receipt_lines"
#     
#     id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
#     receipt_id: Mapped[UUID] = mapped_column(
#         PGUUID(as_uuid=True), 
#         ForeignKey("pos_receipts.id")
#     )
#     # Campos específicos de POS
#     uom: Mapped[str] = mapped_column(String(20), default="unit")
