"""
Compatibility document conversion service.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class DocumentConverter:
    def __init__(self, db: Session):
        self.db = db

    def sales_order_to_invoice(
        self,
        sales_order_id: UUID,
        tenant_id: str | UUID,
        invoice_data: dict[str, Any] | None = None,
    ) -> UUID:
        from app.models.company.company_settings import CompanySettings
        from app.models.core.facturacion import Invoice
        from app.models.core.invoiceLine import LineaFactura
        from app.models.sales.order import SalesOrder, SalesOrderItem
        from app.modules.shared.services.numbering import generar_numero_documento

        order = (
            self.db.query(SalesOrder)
            .filter(SalesOrder.id == sales_order_id, SalesOrder.tenant_id == str(tenant_id))
            .first()
        )
        if not order:
            raise ValueError(f"Orden de venta {sales_order_id} no encontrada")
        if order.status not in ["confirmed", "delivered"]:
            raise ValueError(
                f"La orden debe estar confirmada o entregada (estado actual: {order.status})"
            )

        existing_invoice = self.db.execute(
            text(
                """
                SELECT id FROM invoices
                WHERE metadata::jsonb->>'sales_order_id' = :order_id
                AND tenant_id = :tid
                """
            ),
            {"order_id": str(sales_order_id), "tid": str(tenant_id)},
        ).first()
        if existing_invoice:
            raise ValueError(f"La orden {sales_order_id} ya tiene factura: {existing_invoice[0]}")

        items = (
            self.db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order_id).all()
        )
        if not items:
            raise ValueError(f"La orden {sales_order_id} no tiene items")

        iva_default = Decimal("0")
        settings_row = (
            self.db.query(CompanySettings)
            .filter(CompanySettings.tenant_id == str(tenant_id))
            .first()
        )
        settings_json = (
            settings_row.settings
            if settings_row and isinstance(settings_row.settings, dict)
            else {}
        )
        iva_default_raw = (
            settings_json.get("iva_tasa_defecto") if isinstance(settings_json, dict) else None
        )
        if isinstance(iva_default_raw, (int, float, Decimal)):
            iva_default = Decimal(str(iva_default_raw))

        def _normalize_rate(raw: object) -> Decimal:
            rate = Decimal(str(raw or 0))
            if rate > 1:
                rate = rate / Decimal("100")
            if rate < 0:
                rate = Decimal("0")
            return rate

        subtotal = Decimal("0")
        iva = Decimal("0")
        for item in items:
            line_subtotal = Decimal(str(item.qty)) * Decimal(str(item.unit_price))
            line_rate_raw = item.tax_rate if item.tax_rate is not None else iva_default
            line_rate = _normalize_rate(line_rate_raw)
            line_iva = line_subtotal * line_rate
            subtotal += line_subtotal
            iva += line_iva
        total = subtotal + iva

        numero = generar_numero_documento(self.db, tenant_id, "invoice")
        invoice = Invoice(
            numero=numero,
            tenant_id=tenant_id,
            cliente_id=order.customer_id,
            supplier="",
            fecha_emision=str(self.db.execute(text("SELECT CURRENT_DATE")).scalar()),
            monto=int(total),
            subtotal=float(subtotal),
            iva=float(iva),
            total=float(total),
            estado="draft",
        )
        self.db.add(invoice)
        self.db.flush()

        from app.models.core.products import Product as _Product

        _prod_ids = [it.product_id for it in items if it.product_id]
        _prod_names: dict = {}
        if _prod_ids:
            _rows = (
                self.db.query(_Product.id, _Product.name).filter(_Product.id.in_(_prod_ids)).all()
            )
            _prod_names = {str(r.id): r.name for r in _rows}

        for item in items:
            line_subtotal = Decimal(str(item.qty)) * Decimal(str(item.unit_price))
            line_rate_raw = item.tax_rate if item.tax_rate is not None else iva_default
            line_rate = _normalize_rate(line_rate_raw)
            line_iva = line_subtotal * line_rate
            self.db.add(
                LineaFactura(
                    factura_id=invoice.id,
                    sector="base",
                    description=_prod_names.get(str(item.product_id)) or str(item.product_id),
                    quantity=item.qty,
                    unit_price=item.unit_price,
                    vat=float(line_iva),
                )
            )

        order.status = "invoiced"
        self.db.commit()
        return invoice.id

    def pos_receipt_to_invoice(
        self,
        receipt_id: UUID,
        tenant_id: str | UUID,
        customer_id: UUID,
        invoice_data: dict[str, Any] | None = None,
    ) -> UUID:
        from app.models.core.facturacion import Invoice
        from app.models.core.invoiceLine import LineaFactura
        from app.models.pos.receipt import POSReceipt, POSReceiptLine
        from app.modules.shared.services.numbering import generar_numero_documento

        receipt = (
            self.db.query(POSReceipt)
            .filter(POSReceipt.id == receipt_id, POSReceipt.tenant_id == tenant_id)
            .first()
        )
        if not receipt:
            raise ValueError(f"Recibo POS {receipt_id} no encontrado")
        if receipt.status != "paid":
            raise ValueError(f"El recibo debe estar pagado (estado actual: {receipt.status})")
        if receipt.invoice_id:
            raise ValueError(f"El recibo ya tiene factura: {receipt.invoice_id}")

        numero = generar_numero_documento(self.db, tenant_id, "invoice")
        invoice = Invoice(
            numero=numero,
            tenant_id=tenant_id,
            cliente_id=customer_id,
            supplier="",
            fecha_emision=str(receipt.created_at.date()),
            monto=int(receipt.gross_total),
            subtotal=float(receipt.gross_total - receipt.tax_total),
            iva=float(receipt.tax_total),
            total=float(receipt.gross_total),
            estado="emitida",
        )
        self.db.add(invoice)
        self.db.flush()

        lines = self.db.query(POSReceiptLine).filter(POSReceiptLine.receipt_id == receipt_id).all()
        for line in lines:
            self.db.add(
                LineaFactura(
                    factura_id=invoice.id,
                    sector="pos",
                    descripcion=f"Producto {line.product_id}",
                    cantidad=line.qty,
                    precio_unitario=line.unit_price,
                    iva=line.tax_amount if hasattr(line, "tax_amount") else 0,
                )
            )

        receipt.invoice_id = invoice.id
        receipt.status = "invoiced"
        self.db.commit()
        return invoice.id

    def quote_to_sales_order(
        self, quote_id: int, tenant_id: str | UUID, order_data: dict[str, Any] | None = None
    ) -> int:
        raise NotImplementedError("Módulo de presupuestos (quotes) no implementado aún")

    def get_document_chain(self, document_id: str | UUID, document_type: str) -> dict[str, Any]:
        from app.models.core.facturacion import Invoice
        from app.models.pos.receipt import POSReceipt
        from app.models.sales.order import SalesOrder

        chain = {
            "document_id": str(document_id),
            "document_type": document_type,
            "chain": [],
            "payments": [],
            "timeline": [],
        }

        try:
            if document_type == "invoice":
                invoice = self.db.query(Invoice).filter(Invoice.id == document_id).first()
                if not invoice:
                    raise ValueError(f"Invoice {document_id} not found")

                chain["invoice"] = {
                    "id": str(invoice.id),
                    "numero": invoice.numero,
                    "monto": invoice.monto,
                    "estado": invoice.estado,
                    "fecha_emision": str(invoice.fecha_emision),
                }

                if invoice.metadata and isinstance(invoice.metadata, dict):
                    sales_order_id = invoice.metadata.get("sales_order_id")
                    if sales_order_id:
                        order = (
                            self.db.query(SalesOrder)
                            .filter(SalesOrder.id == sales_order_id)
                            .first()
                        )
                        if order:
                            chain["sales_order"] = {
                                "id": str(order.id),
                                "numero": order.numero,
                                "status": order.status,
                                "created_at": str(order.created_at),
                            }
                            chain["chain"].append("sales_order -> invoice")

                payments = self.db.execute(
                    text(
                        """
                        SELECT id, amount, payment_date, payment_method, status
                        FROM payments
                        WHERE invoice_id = :invoice_id
                        ORDER BY payment_date DESC
                        """
                    ),
                    {"invoice_id": str(invoice.id)},
                ).fetchall()

                chain["payments"] = [
                    {
                        "id": str(p[0]),
                        "amount": float(p[1]),
                        "date": str(p[2]),
                        "method": p[3],
                        "status": p[4],
                    }
                    for p in payments
                ]
            elif document_type == "sales_order":
                order = self.db.query(SalesOrder).filter(SalesOrder.id == document_id).first()
                if not order:
                    raise ValueError(f"Sales Order {document_id} not found")

                chain["sales_order"] = {
                    "id": str(order.id),
                    "numero": order.numero,
                    "status": order.status,
                    "created_at": str(order.created_at),
                }

                invoice = self.db.execute(
                    text(
                        """
                        SELECT id, numero, estado, fecha_emision
                        FROM invoices
                        WHERE metadata::jsonb->>'sales_order_id' = :order_id
                        LIMIT 1
                        """
                    ),
                    {"order_id": str(order.id)},
                ).first()

                if invoice:
                    chain["invoice"] = {
                        "id": str(invoice[0]),
                        "numero": invoice[1],
                        "estado": invoice[2],
                        "fecha_emision": str(invoice[3]),
                    }
                    chain["chain"].append("sales_order -> invoice")
            elif document_type == "pos_receipt":
                receipt = self.db.query(POSReceipt).filter(POSReceipt.id == document_id).first()
                if not receipt:
                    raise ValueError(f"POS Receipt {document_id} not found")

                chain["pos_receipt"] = {
                    "id": str(receipt.id),
                    "number": receipt.receipt_number,
                    "status": receipt.status,
                    "created_at": str(receipt.created_at),
                }

                if receipt.invoice_id:
                    invoice = (
                        self.db.query(Invoice).filter(Invoice.id == receipt.invoice_id).first()
                    )
                    if invoice:
                        chain["invoice"] = {
                            "id": str(invoice.id),
                            "numero": invoice.numero,
                            "estado": invoice.estado,
                        }
                        chain["chain"].append("pos_receipt -> invoice")

            return {"success": True, "data": chain}
        except Exception as e:
            return {"success": False, "error": str(e)}
