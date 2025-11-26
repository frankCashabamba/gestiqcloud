from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class PromoteResult:
    def __init__(self, domain_id: str | None, skipped: bool = False):
        self.domain_id = domain_id
        self.skipped = skipped


class InvoiceHandler:
    @staticmethod
    def promote(
        db: Session,
        tenant_id: UUID,
        normalized: dict[str, Any],
        promoted_id: str | None = None,
        **kwargs,
    ) -> PromoteResult:
        """
        Promociona factura completa a tabla invoices con líneas.
        IMPLEMENTACIÓN REAL - guarda en base de datos.
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        from datetime import date, datetime
        from uuid import uuid4

        from app.models.core.clients import Cliente
        from app.models.core.facturacion import Invoice
        from app.models.core.invoiceLine import LineaFactura

        try:
            # Extraer número de factura
            invoice_number = str(
                normalized.get("invoice_number")
                or normalized.get("numero")
                or normalized.get("numero_factura")
                or normalized.get("number")
                or f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            ).strip()

            # Fecha de emisión
            tx_date_raw = (
                normalized.get("invoice_date")
                or normalized.get("tx_date_emision")
                or normalized.get("tx_date")
                or normalized.get("date")
                or normalized.get("issue_date")
            )
            if isinstance(tx_date_raw, str):
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        tx_date_emision = datetime.strptime(tx_date_raw, fmt).date().isoformat()
                        break
                    except ValueError:
                        continue
                else:
                    tx_date_emision = datetime.utcnow().date().isoformat()
            elif isinstance(tx_date_raw, (date, datetime)):
                tx_date_emision = (
                    tx_date_raw.isoformat()
                    if isinstance(tx_date_raw, date)
                    else tx_date_raw.date().isoformat()
                )
            else:
                tx_date_emision = datetime.utcnow().date().isoformat()

            # Vendor/Supplier
            vendor_name = str(
                normalized.get("vendor_name")
                or normalized.get("vendor")
                or normalized.get("supplier")
                or normalized.get("vendor", {}).get("name")
                or "Unknown vendor"
            ).strip()

            # Importes
            subtotal = float(
                normalized.get("subtotal")
                or normalized.get("base_imponible")
                or normalized.get("totals", {}).get("subtotal")
                or 0
            )
            iva = float(
                normalized.get("tax")
                or normalized.get("iva")
                or normalized.get("impuesto")
                or normalized.get("totals", {}).get("tax")
                or 0
            )
            total = float(
                normalized.get("total")
                or normalized.get("amount")
                or normalized.get("totals", {}).get("total")
                or (subtotal + iva)
            )

            # Buscar o crear cliente/proveedor
            cliente = (
                db.query(Cliente)
                .filter(Cliente.tenant_id == tenant_id, Cliente.nombre == vendor_name)
                .first()
            )
            if not cliente:
                cliente = Cliente(
                    tenant_id=tenant_id,
                    nombre=vendor_name,
                    tipo="proveedor",
                    email=None,
                    telefono=None,
                )
                db.add(cliente)
                db.flush()

            # Crear factura
            invoice = Invoice(
                id=uuid4(),
                tenant_id=tenant_id,
                cliente_id=cliente.id,
                numero=invoice_number,
                proveedor=vendor_name,
                tx_date_emision=tx_date_emision,
                subtotal=subtotal,
                iva=iva,
                total=total,
                monto=int(total),
                estado="pendiente",
            )
            db.add(invoice)
            db.flush()

            # Crear líneas
            lines_data = normalized.get("lines") or normalized.get("lineas") or []
            if not lines_data and total > 0:
                lines_data = [
                    {
                        "descripcion": normalized.get("concept") or "Importe de factura",
                        "cantidad": 1,
                        "precio_unitario": total,
                    }
                ]

            for line in lines_data:
                descripcion = str(
                    line.get("descripcion") or line.get("desc") or line.get("description") or ""
                ).strip()
                if not descripcion:
                    continue

                cantidad = float(
                    line.get("cantidad") or line.get("qty") or line.get("quantity") or 1
                )
                precio_unitario = float(
                    line.get("precio_unitario")
                    or line.get("unit_price")
                    or line.get("precio")
                    or line.get("price")
                    or 0
                )
                iva_linea = float(line.get("iva") or line.get("tax_amount") or 0)

                linea = LineaFactura(
                    id=uuid4(),
                    factura_id=invoice.id,
                    sector="base",
                    descripcion=descripcion,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    iva=iva_linea,
                )
                db.add(linea)

            db.flush()
            return PromoteResult(domain_id=str(invoice.id), skipped=False)

        except Exception:
            return PromoteResult(domain_id=None, skipped=False)


class BankHandler:
    @staticmethod
    def promote(
        db: Session,
        tenant_id: UUID,
        normalized: dict[str, Any],
        promoted_id: str | None = None,
        **kwargs,
    ) -> PromoteResult:
        """
        Promociona transacción bancaria a tabla bank_transactions.
        IMPLEMENTACIÓN REAL - guarda en base de datos.
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        from datetime import date, datetime
        from uuid import uuid4

        from app.models.core.facturacion import (
            BankAccount,
            BankTransaction,
            TransactionStatus,
            TransactionType,
        )

        try:
            # Fecha
            tx_date_raw = (
                normalized.get("date")
                or normalized.get("tx_date")
                or normalized.get("value_date")
                or normalized.get("transaction_date")
                or normalized.get("bank_tx", {}).get("value_date")
            )
            if isinstance(tx_date_raw, str):
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        tx_date = datetime.strptime(tx_date_raw, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    tx_date = datetime.utcnow().date()
            elif isinstance(tx_date_raw, (date, datetime)):
                tx_date = tx_date_raw if isinstance(tx_date_raw, date) else tx_date_raw.date()
            else:
                tx_date = datetime.utcnow().date()

            amount = float(
                normalized.get("amount")
                or normalized.get("monto")
                or normalized.get("bank_tx", {}).get("amount")
                or 0
            )

            direction = (
                normalized.get("direction")
                or normalized.get("bank_tx", {}).get("direction")
                or ("debit" if amount < 0 else "credit")
            )

            if amount < 0:
                amount = abs(amount)

            # Concepto
            concept = str(
                normalized.get("description")
                or normalized.get("concept")
                or normalized.get("narrative")
                or normalized.get("bank_tx", {}).get("narrative")
                or "Bank transaction"
            ).strip()

            # Referencia
            reference = (
                str(
                    normalized.get("reference")
                    or normalized.get("reference")
                    or normalized.get("external_ref")
                    or normalized.get("bank_tx", {}).get("external_ref")
                    or ""
                ).strip()
                or None
            )

            # IBAN
            iban = str(normalized.get("iban") or "").strip() or None

            # Moneda
            currency = str(
                normalized.get("currency")
                or normalized.get("currency")
                or (normalized.get("country") == "EC" and "USD")
                or "EUR"
            ).upper()

            # Find or create bank account
            if iban:
                account = (
                    db.query(BankAccount)
                    .filter(BankAccount.tenant_id == tenant_id, BankAccount.iban == iban)
                    .first()
                )
            else:
                account = db.query(BankAccount).filter(BankAccount.tenant_id == tenant_id).first()

            if not account:
                account = BankAccount(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    name="Main Account",
                    iban=iban or f"ES00-{str(uuid4())[:16]}",
                    bank="Unknown",
                    currency=currency,
                    customer_id=None,
                )
                db.add(account)
                db.flush()

            type_map = {
                "transfer": TransactionType.TRANSFER,
                "transferencia": TransactionType.TRANSFER,
                "card": TransactionType.CARD,
                "tarjeta": TransactionType.CARD,
                "cash": TransactionType.CASH,
                "efectivo": TransactionType.CASH,
                "receipt": TransactionType.RECEIPT,
                "recibo": TransactionType.RECEIPT,
            }
            type_str = str(normalized.get("tipo") or normalized.get("type") or "other").lower()
            tx_type = type_map.get(type_str, TransactionType.OTHER)

            # Crear transacción
            transaction = BankTransaction(
                id=uuid4(),
                tenant_id=tenant_id,
                account_id=account.id,
                date=tx_date,
                amount=amount,
                currency=currency,
                type=tx_type,
                status=TransactionStatus.PENDING,
                concept=concept,
                reference=reference,
                counterparty_name=str(normalized.get("counterparty_name") or "").strip() or None,
                counterparty_iban=str(normalized.get("counterparty_iban") or "").strip() or None,
                source=normalized.get("source") or "import",
                category=str(normalized.get("category") or "").strip() or None,
                direction=direction,
            )
            db.add(transaction)
            db.flush()

            return PromoteResult(domain_id=str(transaction.id), skipped=False)

        except Exception:
            return PromoteResult(domain_id=None, skipped=False)


class ExpenseHandler:
    @staticmethod
    def promote(
        db: Session,
        tenant_id: UUID,
        normalized: dict[str, Any],
        promoted_id: str | None = None,
        **kwargs,
    ) -> PromoteResult:
        """
        Promotes expense/receipt to expenses table.
        REAL IMPLEMENTATION - saves to database.
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        from datetime import date, datetime
        from decimal import Decimal
        from uuid import uuid4

        from app.models.expenses.expense import Expense

        try:
            # Fecha
            tx_date_raw = (
                normalized.get("date")
                or normalized.get("tx_date")
                or normalized.get("expense_date")
                or normalized.get("issue_date")
            )
            if isinstance(tx_date_raw, str):
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                    try:
                        tx_date = datetime.strptime(tx_date_raw, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    tx_date = datetime.utcnow().date()
            elif isinstance(tx_date_raw, (date, datetime)):
                tx_date = tx_date_raw if isinstance(tx_date_raw, date) else tx_date_raw.date()
            else:
                tx_date = datetime.utcnow().date()

            # Concept/Description
            concept = str(
                normalized.get("description") or normalized.get("concept") or "Expense"
            ).strip()

            # Category
            category = (
                str(normalized.get("category") or normalized.get("category") or "otros")
                .strip()
                .lower()
            )

            # Importes
            iva = float(
                normalized.get("tax")
                or normalized.get("iva")
                or normalized.get("totals", {}).get("tax")
                or 0
            )
            total = float(
                normalized.get("total")
                or normalized.get("amount")
                or normalized.get("amount")
                or normalized.get("totals", {}).get("total")
                or 0
            )
            amount = total - iva if iva > 0 else total

            # Forma de pago
            payment_map = {
                "cash": "efectivo",
                "card": "tarjeta",
                "transfer": "transferencia",
                "direct_debit": "domiciliacion",
            }
            forma_pago_raw = str(
                normalized.get("payment_method")
                or normalized.get("forma_pago")
                or normalized.get("payment", {}).get("method")
                or "efectivo"
            ).lower()
            forma_pago = payment_map.get(forma_pago_raw, forma_pago_raw)

            # Número de factura
            factura_numero = (
                str(
                    normalized.get("invoice_number")
                    or normalized.get("numero_factura")
                    or normalized.get("receipt_number")
                    or ""
                ).strip()
                or None
            )

            # Proveedor (opcional)
            proveedor_nombre = str(
                normalized.get("vendor")
                or normalized.get("proveedor")
                or normalized.get("vendor", {}).get("name")
                or ""
            ).strip()

            supplier_id = None
            if proveedor_nombre:
                try:
                    from app.models.suppliers import Supplier

                    supplier = (
                        db.query(Supplier)
                        .filter(
                            Supplier.tenant_id == tenant_id,
                            Supplier.name == proveedor_nombre,
                        )
                        .first()
                    )
                    if supplier:
                        supplier_id = supplier.id
                except Exception:
                    pass

            # User (obtain from context or use generic)
            usuario_id = uuid4()

            # Create expense
            expense = Expense(
                id=uuid4(),
                tenant_id=tenant_id,
                date=tx_date,
                concept=concept,
                category=category,
                subcategory=None,
                amount=Decimal(str(amount)),
                vat=Decimal(str(iva)),
                total=Decimal(str(total)),
                supplier_id=supplier_id,
                payment_method=forma_pago,
                invoice_number=factura_numero,
                status="pending",
                user_id=usuario_id,
                notes=normalized.get("notes") or None,
            )
            db.add(expense)
            db.flush()

            return PromoteResult(domain_id=str(expense.id), skipped=False)

        except Exception:
            return PromoteResult(domain_id=None, skipped=False)


class ProductHandler:
    @staticmethod
    def promote(
        db: Session,
        tenant_id: UUID,
        normalized: dict[str, Any],
        promoted_id: str | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> PromoteResult:
        """Promote validated product data to modern products schema (ORM).

        Fields: name, price, stock, unit, sku, category_id, product_metadata.
        Category is resolved/created in product_categories by name.
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        # Import here to avoid circular dependency
        from app.models.core.product_category import ProductCategory
        from app.models.core.products import Product

        # Extract and validate required fields
        name = str(
            normalized.get("name") or normalized.get("producto") or normalized.get("nombre") or ""
        ).strip()
        if not name:
            return PromoteResult(domain_id=None, skipped=False)

        # Prices and quantities
        price = normalized.get("price") or normalized.get("precio") or normalized.get("pvp") or 0
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = 0.0

        stock = (
            normalized.get("stock") or normalized.get("cantidad") or normalized.get("quantity") or 0
        )
        try:
            stock = float(stock)
        except (ValueError, TypeError):
            stock = 0.0

        # Category resolution
        category_id = None
        category_name = str(normalized.get("category") or normalized.get("category") or "").strip()
        if category_name:
            category = (
                db.query(ProductCategory)
                .filter(
                    ProductCategory.tenant_id == tenant_id,
                    ProductCategory.name == category_name,
                )
                .first()
            )
            if not category:
                category = ProductCategory(tenant_id=tenant_id, name=category_name)
                db.add(category)
                db.flush()
            category_id = category.id

        # SKU generation if missing - usar mismo sistema que create_product
        sku = normalized.get("sku") or normalized.get("codigo") or normalized.get("code")
        if not sku:
            # Generar SKU secuencial: {PREFIX}-{NUM}
            import re

            prefix = "PRO"
            if category_name:
                prefix = re.sub(r"[^A-Z]", "", category_name.upper())[:3] or "PRO"

            # Buscar último SKU con ese prefijo
            result = db.execute(
                text(
                    "SELECT sku FROM products "
                    "WHERE tenant_id = :tid AND sku LIKE :pattern "
                    "ORDER BY sku DESC LIMIT 1"
                ),
                {"tid": str(tenant_id), "pattern": f"{prefix}-%"},
            ).fetchone()

            if result and result[0]:
                match = re.search(r"-(\d+)$", result[0])
                next_num = int(match.group(1)) + 1 if match else 1
            else:
                next_num = 1

            sku = f"{prefix}-{next_num:04d}"

        # Upsert-like: look up existing by tenant + (sku or name)
        existing = (
            db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                (Product.sku == sku) | (Product.name == name),
            )
            .first()
        )

        if existing:
            existing.price = price
            existing.stock = stock
            existing.unit = (
                normalized.get("unit") or normalized.get("unidad") or existing.unit or "unidad"
            )
            try:
                if options and options.get("activate"):
                    existing.activo = True
            except Exception:
                pass
            if category_id:
                existing.category_id = category_id
            # Keep or extend metadata
            meta = dict(existing.product_metadata or {})
            if normalized.get("_amountd_at"):
                meta["amountd_at"] = normalized.get("_amountd_at")
            meta.setdefault("source", "excel_import")
            existing.product_metadata = meta
            db.flush()
            # Inicializar stock_items si procede (sólo primera vez y si hay cantidad)
            try:
                if float(stock or 0) > 0:
                    from app.models.inventory.stock import StockItem
                    from app.models.inventory.warehouse import Warehouse

                    has_si = db.query(StockItem).filter(StockItem.product_id == existing.id).first()
                    if not has_si:
                        # Buscar almacén preferente ALM-1; si no existe, crear uno por defecto
                        target_code = (options or {}).get("target_warehouse")
                        if target_code:
                            wh = (
                                db.query(Warehouse)
                                .filter(
                                    Warehouse.tenant_id == tenant_id,
                                    Warehouse.code == target_code,
                                )
                                .first()
                            )
                            if not wh and (options or {}).get("create_missing_warehouses", True):
                                wh = Warehouse(
                                    tenant_id=tenant_id,
                                    code=target_code,
                                    name=target_code,
                                    is_active=True,
                                )
                                db.add(wh)
                                db.flush()
                        if not (locals().get("wh")):
                            wh = (
                                db.query(Warehouse)
                                .filter(Warehouse.tenant_id == tenant_id)
                                .order_by(Warehouse.code.asc())
                                .first()
                            )
                        if not wh:
                            wh = Warehouse(
                                tenant_id=tenant_id,
                                code="ALM-1",
                                name="Principal",
                                is_active=True,
                            )
                            db.add(wh)
                            db.flush()
                        # Crear stock_item
                        si = StockItem(
                            tenant_id=tenant_id,
                            warehouse_id=str(wh.id),
                            product_id=str(existing.id),
                            qty=float(stock),
                        )
                        db.add(si)
                        db.flush()
                        # Intentar movimiento con columnas existentes (fallback SQL crudo)
                        try:
                            db.execute(
                                text(
                                    "INSERT INTO stock_moves (tenant_id, product_id, warehouse_id, qty, kind) "
                                    "VALUES (:tid, :pid, :wid, :qty, :kind)"
                                ),
                                {
                                    "tid": str(tenant_id),
                                    "pid": str(existing.id),
                                    "wid": str(wh.id),
                                    "qty": float(stock),
                                    "kind": "receipt",
                                },
                            )
                        except Exception:
                            # si la tabla/columnas difieren, continuar sin move
                            pass
            except Exception:
                # No bloquear import si falla la inicialización de stock por alguna razón
                pass
            return PromoteResult(domain_id=str(existing.id), skipped=False)

        # Create new product
        product = Product(
            tenant_id=tenant_id,
            sku=sku,
            name=name,
            price=price,
            stock=stock,
            unit=(normalized.get("unit") or normalized.get("unidad") or "unidad"),
            category_id=category_id,
            product_metadata={
                "amountd_at": normalized.get("_amountd_at"),
                "source": "excel_import",
            },
        )
        try:
            if options and options.get("activate"):
                product.activo = True
        except Exception:
            pass
        db.add(product)
        db.flush()
        # Inicializar stock_items si procede (sólo si hay cantidad y aún no existen)
        try:
            if float(stock or 0) > 0:
                from app.models.inventory.stock import StockItem
                from app.models.inventory.warehouse import Warehouse

                has_si = db.query(StockItem).filter(StockItem.product_id == product.id).first()
                if not has_si:
                    target_code = (options or {}).get("target_warehouse")
                    if target_code:
                        wh = (
                            db.query(Warehouse)
                            .filter(
                                Warehouse.tenant_id == tenant_id,
                                Warehouse.code == target_code,
                            )
                            .first()
                        )
                        if not wh and (options or {}).get("create_missing_warehouses", True):
                            wh = Warehouse(
                                tenant_id=tenant_id,
                                code=target_code,
                                name=target_code,
                                is_active=True,
                            )
                            db.add(wh)
                            db.flush()
                    if not (locals().get("wh")):
                        wh = (
                            db.query(Warehouse)
                            .filter(Warehouse.tenant_id == tenant_id)
                            .order_by(Warehouse.code.asc())
                            .first()
                        )
                    if not wh:
                        wh = Warehouse(
                            tenant_id=tenant_id,
                            code="ALM-1",
                            name="Principal",
                            is_active=True,
                        )
                        db.add(wh)
                        db.flush()
                    si = StockItem(
                        tenant_id=tenant_id,
                        warehouse_id=str(wh.id),
                        product_id=str(product.id),
                        qty=float(stock),
                    )
                    db.add(si)
                    db.flush()
                    try:
                        db.execute(
                            text(
                                "INSERT INTO stock_moves (tenant_id, product_id, warehouse_id, qty, kind) "
                                "VALUES (:tid, :pid, :wid, :qty, :kind)"
                            ),
                            {
                                "tid": str(tenant_id),
                                "pid": str(product.id),
                                "wid": str(wh.id),
                                "qty": float(stock),
                                "kind": "receipt",
                            },
                        )
                    except Exception:
                        pass
        except Exception:
            pass
        return PromoteResult(domain_id=str(product.id), skipped=False)


def publish_to_destination(
    db, tenant_id, doc_type: str, extracted_data: dict[str, Any]
) -> str | None:
    """
    Publica extracted_data a tablas destino según doc_type.

    Args:
        db: SQLAlchemy Session
        tenant_id: UUID del tenant
        doc_type: tipo de documento (factura/recibo/banco/transferencia)
        extracted_data: datos canónicos extraídos

    Returns:
        destination_id: ID del registro creado en tabla destino
    """
    handler_map = {
        "factura": InvoiceHandler,
        "recibo": InvoiceHandler,
        "banco": BankHandler,
        "transferencia": BankHandler,
        "desconocido": ExpenseHandler,
    }

    handler = handler_map.get(doc_type, ExpenseHandler)
    result = handler.promote(extracted_data)

    return result.domain_id if result and not result.skipped else None
