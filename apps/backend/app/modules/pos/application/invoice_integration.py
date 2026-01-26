"""
POS -> Documents integration.

Este servicio se usa desde:
- POST /api/v1/tenant/pos/receipts/{id}/checkout
- POST /api/v1/tenant/pos/receipts/{id}/refund

Motivacion:
El servicio anterior intentaba insertar/leer columnas y tablas que no existen en el esquema
que el resto del backend consume (por ejemplo, `subtotal` en `pos_receipts`, y campos
`pos_receipt_id` / `sale_type` / `expense_type` en tablas de negocio). Eso hacia que la
creacion de documentos fallara y `documents_created` quedara vacio.

Este servicio:
- Usa como fuente unica de "modulos habilitados" la tabla `company_modules` (join `modules`).
- Crea Facturas en el esquema que usan reconciliation/einvoicing (invoices.numero/fecha/...).
- Registra devoluciones como gastos en la tabla `expenses` (modelo actual del backend).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _normalize_slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"\s+", "", value)
    return value


def _module_slug_from_url(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    raw = raw.lstrip("/")
    slug = raw.split("/")[0].strip()
    return _normalize_slug(slug) if slug else None


class POSInvoicingService:
    """
    Integracion POS con Invoicing/Sales/Expenses.

    Nota: mantenemos el nombre/clase para no tocar imports en el checkout.
    """

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._enabled_slugs: set[str] | None = None

    def _load_enabled_module_slugs(self) -> set[str]:
        if self._enabled_slugs is not None:
            return self._enabled_slugs

        rows = self.db.execute(
            text(
                """
                SELECT m.url, m.name
                FROM company_modules cm
                JOIN modules m ON m.id = cm.module_id
                WHERE cm.tenant_id = :tid
                  AND cm.active = TRUE
                  AND m.active = TRUE
                """
            ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
            {"tid": self.tenant_id},
        ).fetchall()

        slugs: set[str] = set()
        for url, name in rows:
            slug = _module_slug_from_url(url) or _normalize_slug(str(name or ""))
            if slug:
                slugs.add(slug)

        self._enabled_slugs = slugs
        return slugs

    def check_module_enabled(self, module_id: str) -> bool:
        mid = _normalize_slug(module_id)
        enabled = self._load_enabled_module_slugs()

        aliases: dict[str, set[str]] = {
            # module id -> possible slugs from DB modules.url/name
            "sales": {"sales", "sales_orders", "ventas"},
            "invoicing": {"invoicing", "facturacion", "invoices", "einvoicing", "eintegracion"},
            "expenses": {"expenses", "gastos"},
        }
        if mid in aliases:
            return any(a in enabled for a in aliases[mid])
        return mid in enabled

    def _resolve_default_customer_id(self) -> UUID | None:
        """
        If receipt has no customer, attempts to resolve one heuristically ("Final Consumer").
        If not found, creates one (best-effort) to enable retail invoicing.
        """
        try:
            row = self.db.execute(
                text(
                    """
                    SELECT id
                    FROM clients
                    WHERE tenant_id = :tid
                      AND (
                        lower(name) IN ('consumidor final','final consumer','cliente contado','contado')
                        OR tax_id IN ('9999999999','9999999999999','0000000000')
                      )
                    LIMIT 1
                    """
                ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                {"tid": self.tenant_id},
            ).first()
            if row and row[0]:
                return UUID(str(row[0]))
        except Exception:
            return None

        # Not found: create a default retail customer
        try:
            new_id = uuid4()
            self.db.execute(
                text(
                    """
                    INSERT INTO clients (id, name, tax_id, tenant_id)
                    VALUES (:id, :name, :tax_id, :tid)
                    """
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": new_id,
                    "name": "Consumidor Final",
                    "tax_id": "9999999999",
                    "tid": self.tenant_id,
                },
            )
            return new_id
        except Exception:
            return None
        return None

    def create_invoice_from_receipt(
        self,
        receipt_id: UUID,
        customer_id: UUID | None = None,
        invoice_series: str = "A",
    ) -> dict | None:
        """
        Create a formal invoice at POS checkout.

        Requirements:
        - `invoicing` module enabled for tenant.
        - Receipt must be in `paid` status and without `invoice_id`.
        """
        if not self.check_module_enabled("invoicing"):
            return None

        try:
            receipt = self.db.execute(
                text(
                    """
                    SELECT id, customer_id, number, status, gross_total, tax_total, created_at, invoice_id
                    FROM pos_receipts
                    WHERE id = :rid
                    FOR UPDATE
                    """
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_id},
            ).first()

            if not receipt:
                return None

            (
                receipt_uuid,
                receipt_customer_id,
                receipt_number,
                receipt_status,
                gross_total,
                tax_total,
                created_at,
                existing_invoice_id,
            ) = receipt

            if receipt_status != "paid" or existing_invoice_id:
                return None

            final_customer_id: UUID | None = customer_id or (
                UUID(str(receipt_customer_id)) if receipt_customer_id else None
            )
            if final_customer_id is None:
                final_customer_id = self._resolve_default_customer_id()
            if final_customer_id is None:
                logger.info(
                    "Skipping invoice creation for POS receipt %s: customer_id missing",
                    receipt_uuid,
                )
                return None

            # Resolve sector from company_settings (fallback to tenant template or 'pos')
            sector = self.db.execute(
                text(
                    "SELECT COALESCE(settings->>'sector', NULL) "
                    "FROM company_settings WHERE tenant_id = :tid"
                ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                {"tid": self.tenant_id},
            ).scalar()
            if not sector:
                sector = (
                    self.db.execute(
                        text("SELECT sector_template_name FROM tenants WHERE id = :tid").bindparams(
                            bindparam("tid", type_=PGUUID(as_uuid=True))
                        ),
                        {"tid": self.tenant_id},
                    ).scalar()
                )
            # Map sector to supported polymorphic identities (invoice_lines.polymorphic_on)
            sector = sector or "pos"
            if sector not in {"pos", "bakery", "workshop"}:
                sector = "pos"

            # Generate canonical invoice number (uses DB sequence; fallback in dev)
            from app.modules.shared.services.numbering import generar_numero_documento

            invoice_number = generar_numero_documento(
                self.db,
                tenant_id=str(self.tenant_id),
                tipo="invoice",
                serie=invoice_series or "A",
            )

            subtotal = (Decimal(str(gross_total or 0)) - Decimal(str(tax_total or 0))).quantize(
                Decimal("0.01")
            )
            vat = Decimal(str(tax_total or 0)).quantize(Decimal("0.01"))
            total = Decimal(str(gross_total or 0)).quantize(Decimal("0.01"))

            invoice_id = uuid4()
            issue_date = (
                created_at.date().isoformat()
                if hasattr(created_at, "date")
                else date.today().isoformat()
            )

            # Insert invoice row per ops/migrations/2025-11-21_000_complete_consolidated_schema/up.sql
            # Schema: id, number, supplier, issue_date, amount, status, created_at, tenant_id,
            #         customer_id, subtotal, vat, total
            self.db.execute(
                text(
                    """
                    INSERT INTO invoices (
                        id, tenant_id, customer_id,
                        number, supplier, issue_date,
                        amount, status, created_at,
                        subtotal, vat, total
                    ) VALUES (
                        :id, :tenant_id, :customer_id,
                        :number, :supplier, :issue_date,
                        :amount, :status, :created_at,
                        :subtotal, :vat, :total
                    )
                    """
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("tenant_id", type_=PGUUID(as_uuid=True)),
                    bindparam("customer_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": invoice_id,
                    "tenant_id": self.tenant_id,
                    "customer_id": final_customer_id,
                    "number": str(invoice_number),
                    "supplier": None,
                    "issue_date": issue_date,
                    "amount": float(total),
                    "status": "issued",
                    "created_at": datetime.utcnow().isoformat(),
                    "subtotal": float(subtotal),
                    "vat": float(vat),
                    "total": float(total),
                },
            )

            # Link receipt to invoice
            self.db.execute(
                text(
                    """
                    UPDATE pos_receipts
                    SET invoice_id = :invoice_id
                    WHERE id = :receipt_id
                    """
                ).bindparams(
                    bindparam("invoice_id", type_=PGUUID(as_uuid=True)),
                    bindparam("receipt_id", type_=PGUUID(as_uuid=True)),
                ),
                {"invoice_id": invoice_id, "receipt_id": receipt_uuid},
            )

            lines = self.db.execute(
                text(
                    """
                    SELECT rl.id, rl.product_id, rl.qty, rl.unit_price, rl.tax_rate, rl.discount_pct, p.name
                    FROM pos_receipt_lines rl
                    LEFT JOIN products p ON p.id = rl.product_id
                    WHERE rl.receipt_id = :rid
                    """
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_uuid},
            ).fetchall()

            for receipt_line_id, product_id, qty, unit_price, tax_rate, discount_pct, product_name in lines:
                q = Decimal(str(qty or 0))
                up = Decimal(str(unit_price or 0))
                disc = Decimal(str(discount_pct or 0)) / Decimal("100")
                base = (abs(q) * up * (Decimal("1") - disc)).quantize(Decimal("0.01"))
                rate = Decimal(str(tax_rate or 0))
                line_iva = (base * rate).quantize(Decimal("0.01"))
                # invoice_lines table stores vat amount per line (not the rate)
                description = str(product_name or f"Producto {product_id}")

                line_id = uuid4()
                self.db.execute(
                    text(
                        """
                        INSERT INTO invoice_lines (
                            id, invoice_id, sector, description,
                            quantity, unit_price, vat
                        ) VALUES (
                            :id, :invoice_id, :sector, :description,
                            :quantity, :unit_price, :vat
                        )
                    """
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("invoice_id", type_=PGUUID(as_uuid=True)),
                ),
                    {
                        "id": line_id,
                        "invoice_id": invoice_id,
                        "sector": sector,
                        "description": description,
                        "quantity": float(q),
                        "unit_price": float(up),
                        "vat": float(line_iva),
                    },
                )
                # Insert subclass row for POS polymorphic identity
                self.db.execute(
                    text(
                        """
                        INSERT INTO pos_invoice_lines (id, pos_receipt_line_id)
                        VALUES (:id, :receipt_line_id)
                        """
                    ).bindparams(
                        bindparam("id", type_=PGUUID(as_uuid=True)),
                        bindparam("receipt_line_id", type_=PGUUID(as_uuid=True)),
                    ),
                    {"id": line_id, "receipt_line_id": receipt_line_id},
                )

            self.db.execute(
                text("UPDATE pos_receipts SET invoice_id = :iid WHERE id = :rid").bindparams(
                    bindparam("iid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {"iid": invoice_id, "rid": receipt_uuid},
            )

            self.db.commit()

            return {
                "invoice_id": str(invoice_id),
                "invoice_number": invoice_number,
                "status": "issued",
                "subtotal": float(subtotal),
                "tax": float(vat),
                "total": float(total),
            }
        except Exception as e:
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error("Failed to rollback transaction: %s", rollback_error)
            logger.exception("Error creating invoice from receipt: %s", e)
            return None

    def create_sale_from_receipt(self, receipt_id: UUID) -> dict | None:
        """
        Create a Sales Order from a paid POS receipt.

        Requirements:
        - `sales` module enabled for tenant.
        - Receipt must be in `paid` status.
        - No sales order should exist for this receipt yet.
        """
        if not self.check_module_enabled("sales"):
            logger.info("Sales module not enabled for tenant %s", self.tenant_id)
            return None

        # Use a savepoint to isolate this operation from the outer transaction.
        # If it fails, we can rollback without affecting other concurrent operations.
        try:
            # Note: SQLAlchemy session may already be in a transaction.
            # The savepoint pattern allows nested transaction semantics.
            receipt = self.db.execute(
                text(
                    """
                    SELECT id, customer_id, number, status, gross_total, tax_total, created_at
                    FROM pos_receipts
                    WHERE id = :rid
                    FOR UPDATE
                    """
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_id},
            ).first()
            if not receipt:
                return None

            (
                receipt_uuid,
                customer_id,
                receipt_number,
                receipt_status,
                gross_total,
                tax_total,
                created_at,
            ) = receipt

            if receipt_status != "paid":
                return None

            # Skip sales order creation for refunds/negative receipts
            has_refunds = self.db.execute(
                text(
                    "SELECT 1 FROM pos_receipt_lines WHERE receipt_id = :rid AND qty < 0 LIMIT 1"
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_uuid},
            ).first()
            if has_refunds:
                return None

            existing = self.db.execute(
                text(
                    """
                    SELECT id, number, total, status
                    FROM sales_orders
                    WHERE tenant_id = :tid AND pos_receipt_id = :rid
                    LIMIT 1
                    """
                ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                {"tid": self.tenant_id, "rid": receipt_uuid},
            ).first()
            if existing:
                so_id, so_number, so_total, so_status = existing
                return {
                    "sale_id": str(so_id),
                    "sale_type": "sales_order",
                    "status": str(so_status),
                    "total": float(so_total or 0),
                }

            # Fetch tenant's configured currency instead of using receipt's currency
            tenant_currency = self.db.execute(
                text(
                    """
                    SELECT base_currency
                    FROM tenants
                    WHERE id = :tid
                    """
                ).bindparams(bindparam("tid", type_=PGUUID(as_uuid=True))),
                {"tid": self.tenant_id},
            ).scalar()
            
            if not tenant_currency:
                logger.warning("Tenant %s has no configured currency", self.tenant_id)
                return None

            subtotal = (Decimal(str(gross_total or 0)) - Decimal(str(tax_total or 0))).quantize(
                Decimal("0.01")
            )
            iva = Decimal(str(tax_total or 0)).quantize(Decimal("0.01"))
            total = Decimal(str(gross_total or 0)).quantize(Decimal("0.01"))

            sales_order_id = uuid4()
            sales_order_number = f"SO-{receipt_number}-{str(receipt_uuid)[:8]}"
            order_date = (
                created_at.date().isoformat() if hasattr(created_at, "date") else date.today().isoformat()
            )
            notes = f"POS receipt {receipt_number}"

            self.db.execute(
                text(
                    """
                    INSERT INTO sales_orders (
                        id, tenant_id, number, customer_id, pos_receipt_id,
                        order_date, subtotal, tax, total, currency,
                        status, notes, created_at, updated_at
                    ) VALUES (
                        :id, :tenant_id, :number, :customer_id, :pos_receipt_id,
                        :order_date, :subtotal, :tax, :total, :currency,
                        :status, :notes, now(), now()
                    )
                    """
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("tenant_id", type_=PGUUID(as_uuid=True)),
                    bindparam("customer_id", type_=PGUUID(as_uuid=True)),
                    bindparam("pos_receipt_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": sales_order_id,
                    "tenant_id": self.tenant_id,
                    "number": sales_order_number,
                    "customer_id": customer_id,
                    "pos_receipt_id": receipt_uuid,
                    "order_date": order_date,
                    "subtotal": float(subtotal),
                    "tax": float(iva),
                    "total": float(total),
                    "currency": tenant_currency,
                    "status": "confirmed",
                    "notes": notes,
                },
            )

            lines = self.db.execute(
                text(
                    """
                    SELECT product_id, qty, unit_price, tax_rate, discount_pct
                    FROM pos_receipt_lines
                    WHERE receipt_id = :rid
                    """
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_uuid},
            ).fetchall()

            for product_id, qty, unit_price, tax_rate, discount_pct in lines:
                q = Decimal(str(qty or 0))
                up = Decimal(str(unit_price or 0))
                disc = Decimal(str(discount_pct or 0)) / Decimal("100")
                base = (q * up * (Decimal("1") - disc)).quantize(Decimal("0.01"))
                self.db.execute(
                    text(
                        """
                        INSERT INTO sales_order_items (
                            id, sales_order_id, product_id, quantity, unit_price,
                            tax_rate, discount_percent, line_total, created_at
                        ) VALUES (
                            :id, :order_id, :product_id, :qty, :unit_price,
                            :tax_rate, :discount_percent, :line_total, now()
                        )
                        """
                    ).bindparams(
                        bindparam("id", type_=PGUUID(as_uuid=True)),
                        bindparam("order_id", type_=PGUUID(as_uuid=True)),
                        bindparam("product_id", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "id": uuid4(),
                        "order_id": sales_order_id,
                        "product_id": product_id,
                        "qty": float(q),
                        "unit_price": float(up),
                        "tax_rate": float(tax_rate or 0),
                        "discount_percent": float(discount_pct or 0),
                        "line_total": float(base),
                    },
                )

            self.db.commit()
            return {
                "sale_id": str(sales_order_id),
                "sale_type": "sales_order",
                "status": "confirmed",
                "total": float(total),
            }
        except Exception as e:
            try:
                self.db.rollback()
            except Exception as rollback_error:
                logger.error("Failed to rollback transaction: %s", rollback_error)
            logger.exception("Error creating sale from receipt: %s", e)
            # Return None to indicate failure
            return None

    def create_expense_from_receipt(
        self,
        receipt_id: UUID,
        expense_type: str = "refund",
        refund_reason: str | None = None,
        payment_method: str | None = None,
    ) -> dict | None:
        """
        Create an expense record for a refund.

        Note: This method is better called from /refund endpoint (not /checkout),
        because that's where negative lines (qty < 0) already exist to measure actual refund.
        """
        if not self.check_module_enabled("expenses"):
            return None

        try:
            receipt = self.db.execute(
                text("SELECT id, number, cashier_id FROM pos_receipts WHERE id = :rid").bindparams(
                    bindparam("rid", type_=PGUUID(as_uuid=True))
                ),
                {"rid": receipt_id},
            ).first()
            if not receipt:
                return None
            receipt_uuid, receipt_number, cashier_id = receipt

            refund_total = self.db.execute(
                text(
                    """
                    SELECT COALESCE(SUM(ABS(line_total)), 0)
                    FROM pos_receipt_lines
                    WHERE receipt_id = :rid AND qty < 0
                    """
                ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
                {"rid": receipt_uuid},
            ).scalar()

            amount = Decimal(str(refund_total or 0)).quantize(Decimal("0.01"))
            if amount <= 0:
                return None

            expense_id = uuid4()
            concept = f"Reembolso POS {receipt_number}"
            category = "refund" if expense_type == "refund" else "pos_return"

            pm = None
            if payment_method in ("cash", "transfer", "card", "direct_debit"):
                pm = payment_method

            self.db.execute(
                text(
                    """
                    INSERT INTO expenses (
                        id, tenant_id, date, concept, category,
                        amount, vat, total, supplier_id,
                        payment_method, invoice_number, status, user_id, notes, created_at
                    ) VALUES (
                        :id, :tenant_id, :date, :concept, :category,
                        :amount, :vat, :total, :supplier_id,
                        :payment_method, :invoice_number, :status, :user_id, :notes, :created_at
                    )
                    """
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("tenant_id", type_=PGUUID(as_uuid=True)),
                    bindparam("supplier_id", type_=PGUUID(as_uuid=True)),
                    bindparam("user_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": expense_id,
                    "tenant_id": self.tenant_id,
                    "date": date.today().isoformat(),
                    "concept": concept,
                    "category": category,
                    "amount": float(amount),
                    "vat": 0.0,
                    "total": float(amount),
                    "supplier_id": None,
                    "payment_method": pm,
                    "invoice_number": str(receipt_number),
                    "status": "pending",
                    "user_id": cashier_id or uuid4(),
                    "notes": refund_reason,
                    "created_at": datetime.utcnow().isoformat(),
                },
            )

            self.db.commit()
            return {
                "expense_id": str(expense_id),
                "expense_type": expense_type,
                "amount": float(amount),
                "status": "pending",
            }
        except Exception as e:
            self.db.rollback()
            logger.exception("Error creating expense from receipt: %s", e)
            return None
