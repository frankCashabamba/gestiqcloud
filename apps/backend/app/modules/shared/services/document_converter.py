"""
Servicio de conversión entre documentos.

Permite convertir entre diferentes tipos de documentos comerciales:
- SalesOrder → Invoice (orden de venta a factura)
- POSReceipt → Invoice (recibo POS a factura formal)
- Quote → SalesOrder (presupuesto a orden)

Mantiene trazabilidad y relaciones entre documentos.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class DocumentConverter:
    """Conversor de documentos comerciales"""

    def __init__(self, db: Session):
        self.db = db

    def sales_order_to_invoice(
        self,
        sales_order_id: int,
        tenant_id: str | UUID,
        invoice_data: dict[str, Any] | None = None,
    ) -> UUID:
        """
        Convierte una orden de venta en factura.

        Args:
            sales_order_id: ID de la orden de venta
            tenant_id: ID del tenant
            invoice_data: Datos adicionales para la factura (opcional)

        Returns:
            ID de la factura creada

        Raises:
            ValueError: Si la orden no existe o ya fue facturada

        Ejemplo:
            converter = DocumentConverter(db)
            invoice_id = converter.sales_order_to_invoice(
                sales_order_id=123,
                tenant_id=tenant_id,
                invoice_data={"payment_terms": "30 days"}
            )
        """
        from app.models.company.company_settings import CompanySettings
        from app.models.core.facturacion import Invoice
        from app.models.core.invoiceLine import LineaFactura
        from app.models.sales.order import SalesOrder, SalesOrderItem
        from app.modules.shared.services.numbering import generar_numero_documento

        # Buscar orden de venta
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

        # Verificar si ya tiene factura
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

        # Obtener items de la orden
        items = (
            self.db.query(SalesOrderItem).filter(SalesOrderItem.order_id == sales_order_id).all()
        )

        if not items:
            raise ValueError(f"La orden {sales_order_id} no tiene items")

        # Obtener IVA default desde CompanySettings (settings.iva_tasa_defecto)
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

        # Calcular totales por linea (usa tax_rate si existe, si no usa IVA default)
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

        # Generar número de factura
        numero = generar_numero_documento(self.db, tenant_id, "invoice")

        # Crear factura
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

        # Crear líneas de factura
        for item in items:
            # TODO: Obtener descripción del producto
            line_subtotal = Decimal(str(item.qty)) * Decimal(str(item.unit_price))
            line_rate_raw = item.tax_rate if item.tax_rate is not None else iva_default
            line_rate = _normalize_rate(line_rate_raw)
            line_iva = line_subtotal * line_rate
            linea = LineaFactura(
                factura_id=invoice.id,
                sector="general",
                descripcion=f"Producto {item.product_id}",
                cantidad=item.qty,
                precio_unitario=item.unit_price,
                iva=float(line_iva),
            )
            self.db.add(linea)

        # Actualizar orden de venta
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
        """
        Convierte un recibo POS en factura formal.

        Caso de uso típico: Cliente B2B compra en tienda física (POS)
        y posteriormente solicita factura formal con datos fiscales.

        Args:
            receipt_id: ID del recibo POS
            tenant_id: ID del tenant
            customer_id: ID del cliente (debe tener datos fiscales)
            invoice_data: Datos adicionales para la factura

        Returns:
            ID de la factura creada

        Raises:
            ValueError: Si el recibo no existe o ya fue facturado

        Ejemplo:
            converter = DocumentConverter(db)
            invoice_id = converter.pos_receipt_to_invoice(
                receipt_id=uuid.UUID("..."),
                tenant_id=tenant_id,
                customer_id=customer_uuid
            )
        """
        from app.models.core.facturacion import Invoice
        from app.models.core.invoiceLine import LineaFactura
        from app.models.pos.receipt import POSReceipt, POSReceiptLine
        from app.modules.shared.services.numbering import generar_numero_documento

        # Buscar recibo
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

        # Generar número de factura
        numero = generar_numero_documento(self.db, tenant_id, "invoice")

        # Crear factura
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
            estado="emitida",  # Ya está pagado, se emite directamente
        )

        self.db.add(invoice)
        self.db.flush()

        # Crear líneas de factura desde líneas de recibo
        lines = self.db.query(POSReceiptLine).filter(POSReceiptLine.receipt_id == receipt_id).all()

        for line in lines:
            # TODO: Obtener descripción del producto
            linea = LineaFactura(
                factura_id=invoice.id,
                sector="pos",
                descripcion=f"Producto {line.product_id}",
                cantidad=line.qty,
                precio_unitario=line.unit_price,
                iva=line.tax_amount if hasattr(line, "tax_amount") else 0,
            )
            self.db.add(linea)

        # Vincular recibo con factura
        receipt.invoice_id = invoice.id
        receipt.status = "invoiced"

        self.db.commit()

        return invoice.id

    def quote_to_sales_order(
        self, quote_id: int, tenant_id: str | UUID, order_data: dict[str, Any] | None = None
    ) -> int:
        """
        Convierte un presupuesto en orden de venta.

        Args:
            quote_id: ID del presupuesto
            tenant_id: ID del tenant
            order_data: Datos adicionales para la orden

        Returns:
            ID de la orden creada

        Note:
            Esta funcionalidad requiere implementar el módulo de presupuestos.
            Se deja como placeholder para desarrollo futuro.
        """
        raise NotImplementedError("Módulo de presupuestos (quotes) no implementado aún")

    def get_document_chain(self, document_id: str | UUID, document_type: str) -> dict[str, Any]:
        """
        Obtiene la cadena completa de documentos relacionados.

        Args:
            document_id: ID del documento
            document_type: Tipo ('invoice', 'sales_order', 'pos_receipt')

        Returns:
            Diccionario con la cadena de documentos:
            {
                'quote_id': ...,
                'sales_order_id': ...,
                'delivery_id': ...,
                'invoice_id': ...,
                'pos_receipt_id': ...,
                'payments': [...]
            }

        Ejemplo:
            chain = converter.get_document_chain(
                document_id=invoice_id,
                document_type='invoice'
            )
            # Devuelve toda la trazabilidad del documento
        """
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
                # Get invoice and trace backwards to source
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

                # Check if comes from sales order
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

                # Get payments
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
                # Get sales order and trace forward
                order = self.db.query(SalesOrder).filter(SalesOrder.id == document_id).first()
                if not order:
                    raise ValueError(f"Sales Order {document_id} not found")

                chain["sales_order"] = {
                    "id": str(order.id),
                    "numero": order.numero,
                    "status": order.status,
                    "created_at": str(order.created_at),
                }

                # Check if has invoice
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
                # Get POS receipt and trace forward
                receipt = self.db.query(POSReceipt).filter(POSReceipt.id == document_id).first()
                if not receipt:
                    raise ValueError(f"POS Receipt {document_id} not found")

                chain["pos_receipt"] = {
                    "id": str(receipt.id),
                    "number": receipt.receipt_number,
                    "status": receipt.status,
                    "created_at": str(receipt.created_at),
                }

                # Check if has invoice
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

            return {
                "success": True,
                "data": chain,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# EJEMPLO DE USO EN ENDPOINT
#
# @router.post("/sales_orders/{order_id}/invoice", response_model=dict)
# def create_invoice_from_order(
#     order_id: int,
#     request: Request,
#     db: Session = Depends(get_db)
# ):
#     """Crear factura desde orden de venta"""
#     tenant_id = request.state.access_claims.get("tenant_id")
#
#     converter = DocumentConverter(db)
#
#     try:
#         invoice_id = converter.sales_order_to_invoice(
#             sales_order_id=order_id,
#             tenant_id=tenant_id
#         )
#         return {"invoice_id": str(invoice_id), "status": "created"}
#
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#
# @router.post("/pos/receipts/{receipt_id}/invoice", response_model=dict)
# def create_invoice_from_receipt(
#     receipt_id: str,
#     payload: dict,
#     request: Request,
#     db: Session = Depends(get_db)
# ):
#     """Crear factura formal desde recibo POS"""
#     tenant_id = request.state.access_claims.get("tenant_id")
#     customer_id = payload.get("customer_id")
#
#     if not customer_id:
#         raise HTTPException(
#             status_code=400,
#             detail="customer_id requerido para factura formal"
#         )
#
#     converter = DocumentConverter(db)
#
#     try:
#         invoice_id = converter.pos_receipt_to_invoice(
#             receipt_id=UUID(receipt_id),
#             tenant_id=tenant_id,
#             customer_id=UUID(customer_id)
#         )
#         return {"invoice_id": str(invoice_id), "status": "created"}
#
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
