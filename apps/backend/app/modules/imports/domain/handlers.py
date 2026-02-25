from __future__ import annotations

import logging
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.core.product_category import ProductCategory
from app.models.core.products import Product
from app.modules.imports.application.sku_utils import sanitize_sku
from app.services.inventory_costing import InventoryCostingService


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
            raw_invoice_number = (
                normalized.get("invoice_number")
                or normalized.get("numero")
                or normalized.get("numero_factura")
                or normalized.get("number")
            )
            # Extraer número de factura
            invoice_number = str(
                raw_invoice_number or f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
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

            # Search or create client/supplier
            cliente = (
                db.query(Cliente)
                .filter(Cliente.tenant_id == tenant_id, Cliente.name == vendor_name)
                .first()
            )
            if not cliente:
                cliente = Cliente(
                    tenant_id=tenant_id,
                    name=vendor_name,
                    email=None,
                    phone=None,
                )
                db.add(cliente)
                db.flush()

            # Dedupe de negocio para facturas:
            # 1) número de factura (+proveedor si existe)
            # 2) fallback por proveedor+fecha+total cuando no hay número confiable
            existing_invoice = None
            if raw_invoice_number and str(raw_invoice_number).strip():
                q = db.query(Invoice).filter(
                    Invoice.tenant_id == tenant_id,
                    func.lower(Invoice.number) == invoice_number.lower(),
                )
                if vendor_name and vendor_name != "Unknown vendor":
                    q = q.filter(func.lower(Invoice.supplier) == vendor_name.lower())
                existing_invoice = q.first()
            else:
                existing_invoice = (
                    db.query(Invoice)
                    .filter(
                        Invoice.tenant_id == tenant_id,
                        func.lower(Invoice.supplier) == vendor_name.lower(),
                        Invoice.issue_date == tx_date_emision,
                        Invoice.total == total,
                    )
                    .first()
                )
            if existing_invoice:
                return PromoteResult(domain_id=str(existing_invoice.id), skipped=True)

            # Crear factura
            invoice = Invoice(
                id=uuid4(),
                tenant_id=tenant_id,
                customer_id=cliente.id,
                number=invoice_number,
                supplier=vendor_name,
                issue_date=tx_date_emision,
                subtotal=subtotal,
                vat=iva,
                total=total,
                amount=int(total),
                status="pendiente",
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
                    invoice_id=invoice.id,
                    sector="base",
                    description=descripcion,
                    quantity=cantidad,
                    unit_price=precio_unitario,
                    vat=iva_linea,
                )
                db.add(linea)

            db.flush()
            return PromoteResult(domain_id=str(invoice.id), skipped=False)

        except Exception as exc:
            # Do not swallow promotion errors; callers expect to mark the ImportItem as failed.
            logging.getLogger(__name__).exception("InvoiceHandler.promote failed: %s", exc)
            raise


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

            # Dedupe de negocio para movimientos bancarios:
            # 1) referencia (+fecha/monto cuando existen)
            # 2) fallback por fecha+monto+concepto
            existing_tx = None
            if reference:
                q = db.query(BankTransaction).filter(
                    BankTransaction.tenant_id == tenant_id,
                    func.lower(BankTransaction.reference) == reference.lower(),
                )
                if tx_date:
                    q = q.filter(BankTransaction.date == tx_date)
                if amount is not None:
                    q = q.filter(BankTransaction.amount == amount)
                existing_tx = q.first()
            if not existing_tx:
                existing_tx = (
                    db.query(BankTransaction)
                    .filter(
                        BankTransaction.tenant_id == tenant_id,
                        BankTransaction.date == tx_date,
                        BankTransaction.amount == amount,
                        func.lower(BankTransaction.concept) == concept.lower(),
                    )
                    .first()
                )
            if existing_tx:
                return PromoteResult(domain_id=str(existing_tx.id), skipped=True)

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

        except Exception as exc:
            logging.getLogger(__name__).exception("BankHandler.promote failed: %s", exc)
            raise


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
        Only called when user explicitly confirms via the Promote button.
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

            concept = str(
                normalized.get("description") or normalized.get("concept") or "Expense"
            ).strip()

            category = str(normalized.get("category") or "otros").strip().lower()

            iva = float(
                normalized.get("tax")
                or normalized.get("iva")
                or normalized.get("totals", {}).get("tax")
                or 0
            )
            total = float(
                normalized.get("total")
                or normalized.get("amount")
                or normalized.get("totals", {}).get("total")
                or 0
            )
            amount = total - iva if iva > 0 else total

            # Skip expenses with zero or negative total
            if total <= 0:
                return PromoteResult(domain_id=None, skipped=True)

            forma_pago_raw = str(
                normalized.get("payment_method")
                or normalized.get("forma_pago")
                or normalized.get("payment", {}).get("method")
                or "efectivo"
            ).lower()

            factura_numero = (
                str(
                    normalized.get("invoice_number")
                    or normalized.get("numero_factura")
                    or normalized.get("receipt_number")
                    or ""
                ).strip()
                or None
            )

            supplier_id = None
            supplier_name = str(
                normalized.get("vendor") or normalized.get("proveedor") or ""
            ).strip()
            if supplier_name:
                try:
                    from app.models.suppliers import Supplier

                    supplier = (
                        db.query(Supplier)
                        .filter(
                            Supplier.tenant_id == tenant_id,
                            Supplier.name == supplier_name,
                        )
                        .first()
                    )
                    if supplier:
                        supplier_id = supplier.id
                except Exception:
                    pass

            options = kwargs.get("options") or {}
            raw_user_id = options.get("user_id")
            try:
                usuario_id = (
                    raw_user_id if isinstance(raw_user_id, UUID) else UUID(str(raw_user_id))
                )
            except Exception:
                usuario_id = uuid4()

            desired_status = (options.get("payment_status") or "pending").strip().lower()
            if desired_status not in ("pending", "paid"):
                desired_status = "pending"
            payment_method_override = (options.get("payment_method") or "").strip().lower() or None

            # Dedupe
            existing_expense = None
            if factura_numero:
                q = db.query(Expense).filter(
                    Expense.tenant_id == tenant_id,
                    func.lower(Expense.invoice_number) == factura_numero.lower(),
                )
                if supplier_id:
                    q = q.filter(Expense.supplier_id == supplier_id)
                existing_expense = q.first()
            if not existing_expense:
                existing_expense = (
                    db.query(Expense)
                    .filter(
                        Expense.tenant_id == tenant_id,
                        Expense.date == tx_date,
                        func.lower(Expense.concept) == concept.lower(),
                        Expense.total == Decimal(str(total)),
                    )
                    .first()
                )
            if existing_expense:
                return PromoteResult(domain_id=str(existing_expense.id), skipped=True)

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
                payment_method=payment_method_override or forma_pago_raw,
                invoice_number=factura_numero,
                status="paid" if desired_status == "paid" else "pending",
                user_id=usuario_id,
                notes=normalized.get("notes") or None,
            )
            db.add(expense)
            db.flush()

            return PromoteResult(domain_id=str(expense.id), skipped=False)

        except Exception as exc:
            logging.getLogger(__name__).exception("ExpenseHandler.promote failed: %s", exc)
            raise


class ProductHandler:
    @staticmethod
    def _to_dec(value: float | Decimal | None, q: str = "0.000001") -> Decimal:
        if value is None:
            value = 0
        return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)

    @staticmethod
    def _resolve_unit_cost(normalized: dict[str, Any]) -> Decimal:
        candidates = (
            normalized.get("cost_price"),
            normalized.get("cost"),
            normalized.get("unit_cost"),
            normalized.get("purchase_price"),
            normalized.get("purchase_cost"),
        )
        for value in candidates:
            if value is None:
                continue
            try:
                return ProductHandler._to_dec(float(value), "0.000001")
            except (TypeError, ValueError):
                continue
        return ProductHandler._to_dec(0, "0.000001")

    @staticmethod
    def _normalize_name(value: str | None) -> str:
        if not value:
            return ""
        txt = unicodedata.normalize("NFKD", str(value))
        txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
        txt = txt.lower().strip()
        txt = re.sub(r"[^a-z0-9\s]+", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        return txt

    @staticmethod
    def _normalize_name_tokens(value: str | None) -> list[str]:
        base = ProductHandler._normalize_name(value)
        if not base:
            return []
        tokens = [t for t in base.split(" ") if t]
        out: list[str] = []
        for tok in tokens:
            if len(tok) > 3 and tok.endswith("s"):
                out.append(tok[:-1])
            else:
                out.append(tok)
        return out

    @staticmethod
    def _is_similar_product_name(left: str | None, right: str | None) -> bool:
        a_tokens = ProductHandler._normalize_name_tokens(left)
        b_tokens = ProductHandler._normalize_name_tokens(right)
        if not a_tokens or not b_tokens:
            return False
        a = " ".join(a_tokens)
        b = " ".join(b_tokens)
        if a == b:
            return True
        if a in b or b in a:
            # Accept inclusions when strings are close enough.
            min_len = min(len(a), len(b))
            max_len = max(len(a), len(b))
            if min_len >= 4 and (min_len / max_len) >= 0.6:
                return True
        ratio = SequenceMatcher(None, a, b).ratio()
        if ratio >= 0.88:
            return True
        # Token overlap fallback (e.g. "pan tapado" vs "tapados")
        a_set = set(a_tokens)
        b_set = set(b_tokens)
        overlap = len(a_set.intersection(b_set))
        return overlap > 0 and (overlap / max(min(len(a_set), len(b_set)), 1)) >= 0.75

    @staticmethod
    def _find_existing_product(
        db: Session,
        tenant_id: UUID,
        *,
        sku: str | None,
        name: str,
    ) -> Product | None:
        if sku:
            by_sku = (
                db.query(Product)
                .filter(
                    Product.tenant_id == tenant_id,
                    Product.sku == sku,
                )
                .first()
            )
            if by_sku:
                return by_sku

        # Fast path: case-insensitive exact name match in DB.
        by_name_ci = (
            db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                func.lower(Product.name) == name.lower(),
            )
            .first()
        )
        if by_name_ci:
            return by_name_ci

        # Robust fallback: normalize accents/punctuation/spacing and match in Python.
        target = ProductHandler._normalize_name(name)
        if not target:
            return None

        probe = target.split(" ")[0]
        query = db.query(Product).filter(Product.tenant_id == tenant_id)
        if probe:
            query = query.filter(Product.name.ilike(f"%{probe}%"))
        candidates = query.limit(2000).all()
        for cand in candidates:
            if ProductHandler._normalize_name(cand.name) == target:
                return cand
            if ProductHandler._is_similar_product_name(cand.name, name):
                return cand
        return None

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

        # Extract and validate required fields
        name = str(
            normalized.get("name") or normalized.get("producto") or normalized.get("nombre") or ""
        ).strip()
        if not name:
            return PromoteResult(domain_id=None, skipped=False)

        skip_stock_init = bool(options and options.get("skip_stock_init"))

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

        unit_cost = ProductHandler._resolve_unit_cost(normalized)

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
        sku = sanitize_sku(sku)

        # Upsert-like: look up existing by tenant + sku/name (normalized for name).
        existing = ProductHandler._find_existing_product(
            db,
            tenant_id,
            sku=sku,
            name=name,
        )

        if existing:
            if sku and not existing.sku:
                existing.sku = sku
            existing.price = price
            existing.stock = stock
            if unit_cost > 0:
                existing.cost_price = float(unit_cost)
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
            if skip_stock_init:
                return PromoteResult(domain_id=str(existing.id), skipped=False)
            # Inicializar stock_items si procede (sólo primera vez y si hay cantidad)
            nested = db.begin_nested()
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
                    costing = InventoryCostingService(db)
                    qty_dec = ProductHandler._to_dec(stock)
                    costing.apply_inbound(
                        str(tenant_id),
                        str(wh.id),
                        str(existing.id),
                        qty=qty_dec,
                        unit_cost=unit_cost,
                        initial_qty=ProductHandler._to_dec(0),
                        initial_avg_cost=unit_cost,
                    )
                    # Intentar movimiento con columnas existentes (fallback SQL crudo)
                    try:
                        db.execute(
                            text(
                                "INSERT INTO stock_moves (tenant_id, product_id, warehouse_id, qty, kind, tentative, posted, unit_cost, total_cost, occurred_at) "
                                "VALUES (:tid, :pid, :wid, :qty, :kind, :tentative, :posted, :uc, :tc, NOW())"
                            ),
                            {
                                "tid": str(tenant_id),
                                "pid": str(existing.id),
                                "wid": str(wh.id),
                                "qty": float(stock),
                                "kind": "receipt",
                                "tentative": False,
                                "posted": False,
                                "uc": float(unit_cost),
                                "tc": float(unit_cost * qty_dec),
                            },
                        )
                    except Exception as move_err:
                        logging.warning("Stock move insert skipped: %s", move_err)
            except Exception as stock_err:
                nested.rollback()
                logging.warning(
                    "Stock initialization skipped for product %s: %s", existing.id, stock_err
                )
            else:
                try:
                    nested.commit()
                except Exception as stock_err:
                    nested.rollback()
                    logging.warning(
                        "Stock initialization commit skipped for product %s: %s",
                        existing.id,
                        stock_err,
                    )
            return PromoteResult(domain_id=str(existing.id), skipped=False)

        # Create new product
        product = Product(
            tenant_id=tenant_id,
            sku=sku,
            name=name,
            price=price,
            cost_price=float(unit_cost) if unit_cost > 0 else None,
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
        if skip_stock_init:
            return PromoteResult(domain_id=str(product.id), skipped=False)
        # Inicializar stock_items si procede (sólo si hay cantidad y aún no existen)
        nested = db.begin_nested()
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
                    costing = InventoryCostingService(db)
                    qty_dec = ProductHandler._to_dec(stock)
                    costing.apply_inbound(
                        str(tenant_id),
                        str(wh.id),
                        str(product.id),
                        qty=qty_dec,
                        unit_cost=unit_cost,
                        initial_qty=ProductHandler._to_dec(0),
                        initial_avg_cost=unit_cost,
                    )
                    try:
                        db.execute(
                            text(
                                "INSERT INTO stock_moves (tenant_id, product_id, warehouse_id, qty, kind, tentative, posted, unit_cost, total_cost, occurred_at) "
                                "VALUES (:tid, :pid, :wid, :qty, :kind, :tentative, :posted, :uc, :tc, NOW())"
                            ),
                            {
                                "tid": str(tenant_id),
                                "pid": str(product.id),
                                "wid": str(wh.id),
                                "qty": float(stock),
                                "kind": "receipt",
                                "tentative": False,
                                "posted": False,
                                "uc": float(unit_cost),
                                "tc": float(unit_cost * qty_dec),
                            },
                        )
                    except Exception as move_err:
                        logging.warning("Stock move insert skipped: %s", move_err)
        except Exception as stock_err:
            nested.rollback()
            logging.warning(
                "Stock initialization skipped for new product %s: %s", product.id, stock_err
            )
        else:
            try:
                nested.commit()
            except Exception as stock_err:
                nested.rollback()
                logging.warning(
                    "Stock initialization commit skipped for new product %s: %s",
                    product.id,
                    stock_err,
                )
        return PromoteResult(domain_id=str(product.id), skipped=False)


class RecipeHandler:
    """Handler for promoting recipes from imports to the recipes module."""

    @staticmethod
    def promote(
        db: Session,
        tenant_id: UUID,
        normalized: dict[str, Any],
        promoted_id: str | None = None,
        *,
        options: dict[str, Any] | None = None,
    ) -> PromoteResult:
        """Promote recipe data - this is a placeholder that just returns skipped.

        Actual recipe promotion is handled by _persist_recipes in task_import_file.py
        """
        if promoted_id:
            return PromoteResult(domain_id=promoted_id, skipped=True)

        # For now, recipes are handled separately via _persist_recipes
        # This handler is mainly to satisfy the routing logic
        return PromoteResult(domain_id=None, skipped=True)


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
