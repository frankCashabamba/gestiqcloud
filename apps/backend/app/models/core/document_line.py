"""
Base models for commercial document lines.

Provides a common structure for:
- Invoices (invoice_lines)
- Sales orders (sales_order_items)
- POS receipts (pos_receipt_lines)
- Purchase orders (purchase_order_lines)
"""

from uuid import UUID

from sqlalchemy import Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column


class DocumentLineBase:
    """
    Abstract mixin for all document lines.

    Not mapped to a table; only provides common fields.
    """

    product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Product (can be null for free-text lines)",
    )

    description: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="Item/service description"
    )

    qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, comment="Quantity")

    unit_price: Mapped[float] = mapped_column(
        Numeric(12, 4), nullable=False, default=0, comment="Unit price before tax"
    )

    tax_rate: Mapped[float] = mapped_column(
        Numeric(6, 4), nullable=False, default=0, comment="Tax rate (0.21 = 21%)"
    )

    discount_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, comment="Discount % (10 = 10%)"
    )

    @property
    def subtotal(self) -> float:
        """Subtotal before discounts and taxes."""
        return float(self.qty * self.unit_price)

    @property
    def discount_amount(self) -> float:
        """Discount amount."""
        return float(self.subtotal * (self.discount_pct / 100))

    @property
    def base_amount(self) -> float:
        """Tax base (after discount, before taxes)."""
        return float(self.subtotal - self.discount_amount)

    @property
    def tax_amount(self) -> float:
        """Tax amount."""
        return float(self.base_amount * self.tax_rate)

    @property
    def total(self) -> float:
        """Line total (base + taxes)."""
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
