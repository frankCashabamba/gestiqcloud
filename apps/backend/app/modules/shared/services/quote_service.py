"""Quote/Presupuesto service implementation"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class QuoteService:
    """Service for managing quotes/presupuestos"""

    def __init__(self, db: Session):
        self.db = db

    def create_quote(
        self,
        tenant_id: str | UUID,
        customer_id: UUID,
        items: list[dict[str, Any]],
        expiry_days: int = 30,
        notes: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """
        Create a quote

        Args:
            tenant_id: Tenant ID
            customer_id: Customer ID
            items: List of quote items with product_id, qty, unit_price
            expiry_days: Days until quote expires
            notes: Additional notes
            metadata: Extra metadata

        Returns:
            Quote creation result
        """
        try:
            from app.models.core.facturacion import Invoice
            from app.modules.shared.services.numbering import generar_numero_documento

            # Generate quote number
            numero = generar_numero_documento(self.db, tenant_id, "quote")

            # Calculate totals
            subtotal = Decimal("0")
            iva = Decimal("0")

            for item in items:
                qty = Decimal(str(item.get("qty", 0)))
                unit_price = Decimal(str(item.get("unit_price", 0)))
                tax_rate = Decimal(str(item.get("tax_rate", 0))) / 100

                line_subtotal = qty * unit_price
                line_iva = line_subtotal * tax_rate

                subtotal += line_subtotal
                iva += line_iva

            total = subtotal + iva

            # Create quote (using invoices table with special metadata)
            quote = Invoice(
                numero=numero,
                tenant_id=tenant_id,
                cliente_id=customer_id,
                supplier="",
                fecha_emision=self.db.execute(
                    text("SELECT CURRENT_DATE")
                ).scalar(),
                monto=int(total),
                subtotal=float(subtotal),
                iva=float(iva),
                total=float(total),
                estado="draft",
                metadata={
                    "type": "quote",
                    "items": items,
                    "notes": notes,
                    "expiry_days": expiry_days,
                    **(metadata or {}),
                },
            )

            self.db.add(quote)
            self.db.flush()

            return {
                "success": True,
                "quote_id": str(quote.id),
                "quote_number": numero,
                "subtotal": float(subtotal),
                "iva": float(iva),
                "total": float(total),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def quote_to_sales_order(
        self,
        tenant_id: str | UUID,
        quote_id: UUID,
        order_data: dict | None = None,
    ) -> int:
        """
        Convert quote to sales order

        Args:
            tenant_id: Tenant ID
            quote_id: Quote ID
            order_data: Additional order data

        Returns:
            Sales order ID
        """
        try:
            from app.models.core.invoiceLine import LineaFactura
            from app.models.sales.order import SalesOrder, SalesOrderItem
            from app.models.core.facturacion import Invoice
            from app.modules.shared.services.numbering import generar_numero_documento

            # Get quote
            quote = self.db.query(Invoice).filter(
                Invoice.id == quote_id,
                Invoice.tenant_id == str(tenant_id),
            ).first()

            if not quote:
                raise ValueError(f"Quote {quote_id} not found")

            if not quote.metadata or quote.metadata.get("type") != "quote":
                raise ValueError(f"Document {quote_id} is not a quote")

            # Get quote items
            quote_items = quote.metadata.get("items", [])

            if not quote_items:
                raise ValueError("Quote has no items")

            # Generate order number
            numero = generar_numero_documento(self.db, tenant_id, "sales_order")

            # Create sales order
            order = SalesOrder(
                numero=numero,
                tenant_id=tenant_id,
                customer_id=quote.cliente_id,
                status="pending",
                order_date=self.db.execute(
                    text("SELECT CURRENT_DATE")
                ).scalar(),
                total=quote.total,
            )

            self.db.add(order)
            self.db.flush()

            # Add items to order
            for item in quote_items:
                order_item = SalesOrderItem(
                    order_id=order.id,
                    product_id=item.get("product_id"),
                    qty=item.get("qty"),
                    unit_price=item.get("unit_price"),
                    tax_rate=item.get("tax_rate"),
                )
                self.db.add(order_item)

            # Mark quote as converted
            quote.estado = "converted"
            if not quote.metadata:
                quote.metadata = {}
            quote.metadata["converted_to_sales_order"] = str(order.id)

            self.db.commit()

            return order.id

        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Failed to convert quote: {e}")

    def get_quote(self, quote_id: UUID, tenant_id: str | UUID) -> dict:
        """Get quote details"""
        try:
            from app.models.core.facturacion import Invoice

            quote = self.db.query(Invoice).filter(
                Invoice.id == quote_id,
                Invoice.tenant_id == str(tenant_id),
            ).first()

            if not quote or not quote.metadata or quote.metadata.get("type") != "quote":
                return {"success": False, "error": "Quote not found"}

            return {
                "success": True,
                "quote": {
                    "id": str(quote.id),
                    "numero": quote.numero,
                    "cliente_id": str(quote.cliente_id),
                    "subtotal": quote.subtotal,
                    "iva": quote.iva,
                    "total": quote.total,
                    "items": quote.metadata.get("items", []),
                    "notes": quote.metadata.get("notes", ""),
                    "estado": quote.estado,
                    "created_at": str(quote.fecha_emision),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_quotes(
        self,
        tenant_id: str | UUID,
        customer_id: UUID | None = None,
        status: str | None = None,
    ) -> dict:
        """List quotes for tenant"""
        try:
            from app.models.core.facturacion import Invoice

            query = self.db.query(Invoice).filter(
                Invoice.tenant_id == str(tenant_id),
            )

            # Filter by metadata type = quote
            query = query.filter(
                Invoice.metadata["type"].astext == "quote"
            )

            if customer_id:
                query = query.filter(Invoice.cliente_id == str(customer_id))

            if status:
                query = query.filter(Invoice.estado == status)

            quotes = query.order_by(Invoice.fecha_emision.desc()).all()

            return {
                "success": True,
                "quotes": [
                    {
                        "id": str(q.id),
                        "numero": q.numero,
                        "cliente_id": str(q.cliente_id),
                        "total": q.total,
                        "estado": q.estado,
                        "created_at": str(q.fecha_emision),
                    }
                    for q in quotes
                ],
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_quote(
        self,
        tenant_id: str | UUID,
        quote_id: UUID,
        updates: dict,
    ) -> dict:
        """Update quote"""
        try:
            from app.models.core.facturacion import Invoice

            quote = self.db.query(Invoice).filter(
                Invoice.id == quote_id,
                Invoice.tenant_id == str(tenant_id),
            ).first()

            if not quote:
                return {"success": False, "error": "Quote not found"}

            # Update fields
            if "items" in updates:
                if not quote.metadata:
                    quote.metadata = {}
                quote.metadata["items"] = updates["items"]

            if "notes" in updates:
                if not quote.metadata:
                    quote.metadata = {}
                quote.metadata["notes"] = updates["notes"]

            if "estado" in updates:
                quote.estado = updates["estado"]

            self.db.commit()

            return {
                "success": True,
                "quote_id": str(quote.id),
            }

        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
