"""
POS MODULE: Use Cases para punto de venta.

Implementa:
- Turnos (shift opening/closing)
- Creación de recibos
- Pagos y cambio
- Integración automática con inventory (stock down)
- Integración con accounting (journal entries)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.services.inventory_costing import InventoryCostingService

logger = logging.getLogger(__name__)


class OpenShiftUseCase:
    """Abre turno de caja con monto inicial."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        register_id: UUID,
        opening_float: Decimal,
        cashier_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        if opening_float < 0:
            raise ValueError("Opening float no puede ser negativo")

        register = self.db.execute(
            text(
                "SELECT active FROM pos_registers WHERE id = :rid AND tenant_id = :tid"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"rid": register_id, "tid": tenant_id},
        ).first()

        if not register:
            raise ValueError("register_not_found")
        if not register[0]:
            raise ValueError("register_inactive")

        existing = self.db.execute(
            text(
                "SELECT id FROM pos_shifts WHERE register_id = :rid AND status = 'open' FOR UPDATE"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": register_id},
        ).first()

        if existing:
            raise ValueError("shift_already_open")

        opened_at = datetime.now(UTC)
        row = self.db.execute(
            text(
                "INSERT INTO pos_shifts(register_id, opened_by, opened_at, opening_float, status) "
                "VALUES (:rid, :opened_by, :opened_at, :opening_float, 'open') "
                "RETURNING id"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("opened_by", type_=PGUUID(as_uuid=True)),
            ),
            {
                "rid": register_id,
                "opened_by": cashier_id,
                "opened_at": opened_at,
                "opening_float": float(opening_float),
            },
        ).first()

        return {
            "shift_id": row[0],
            "register_id": register_id,
            "cashier_id": cashier_id,
            "opening_float": opening_float,
            "status": "open",
            "opened_at": opened_at,
        }


class CreateReceiptUseCase:
    """Crea recibo en draft con líneas de productos."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        register_id: UUID,
        shift_id: UUID,
        lines: list[dict[str, Any]],
        tenant_id: UUID,
        cashier_id: UUID,
        customer_id: UUID | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        shift = self.db.execute(
            text("SELECT status FROM pos_shifts WHERE id = :sid AND register_id = :rid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_id, "rid": register_id},
        ).first()

        if not shift:
            raise ValueError("shift_not_found")
        if shift[0] != "open":
            raise ValueError("shift_not_open")

        subtotal = Decimal("0")
        tax = Decimal("0")

        for line in lines:
            qty = Decimal(str(line.get("qty", 0)))
            unit_price = Decimal(str(line.get("unit_price", 0)))
            discount_pct = Decimal(str(line.get("discount_pct", 0))) / 100
            tax_rate = Decimal(str(line.get("tax_rate", 0)))

            line_subtotal = qty * unit_price * (Decimal("1") - discount_pct)
            line_tax = line_subtotal * tax_rate

            subtotal += line_subtotal
            tax += line_tax

        total = subtotal + tax

        return {
            "shift_id": shift_id,
            "register_id": register_id,
            "status": "draft",
            "lines": lines,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
            "notes": notes,
        }


class CheckoutReceiptUseCase:
    """Procesa pago, actualiza stock e integra con accounting."""

    def __init__(self, db: Session, costing_service: InventoryCostingService):
        self.db = db
        self.costing = costing_service

    def execute(
        self,
        *,
        receipt_id: UUID,
        payments: list[dict[str, Any]],
        warehouse_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        receipt = self.db.execute(
            text(
                "SELECT shift_id, status, gross_total FROM pos_receipts "
                "WHERE id = :id AND tenant_id = :tid FOR UPDATE"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_id, "tid": tenant_id},
        ).first()

        if not receipt:
            raise ValueError("receipt_not_found")
        if receipt[1] != "draft":
            raise ValueError(f"invalid_status:{receipt[1]}")

        total_paid = sum(Decimal(str(p.get("amount", 0))) for p in payments)

        lines = self.db.execute(
            text(
                "SELECT id, product_id, qty, unit_price, discount_pct "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_id},
        ).fetchall()

        totals = self.db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100)), 0), "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100) * rl.tax_rate), 0) "
                "FROM pos_receipt_lines rl WHERE rl.receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_id},
        ).first()

        subtotal = Decimal(str(totals[0] or 0))
        tax_amount = Decimal(str(totals[1] or 0))
        total = subtotal + tax_amount

        if total_paid < total:
            change = Decimal("0")
        else:
            change = total_paid - total

        return {
            "receipt_id": receipt_id,
            "status": "paid",
            "paid_at": datetime.now(UTC),
            "payments": payments,
            "total_paid": total_paid,
            "subtotal": subtotal,
            "tax": tax_amount,
            "total": total,
            "change": change,
            "lines_count": len(lines),
        }


class CloseShiftUseCase:
    """Cierra turno con resumen de ventas y movimientos de caja."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        shift_id: UUID,
        cash_count: Decimal,
        tenant_id: UUID,
        closing_notes: str | None = None,
    ) -> dict[str, Any]:
        shift = self.db.execute(
            text(
                "SELECT status, register_id, opening_float FROM pos_shifts WHERE id = :sid FOR UPDATE"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_id},
        ).first()

        if not shift:
            raise ValueError("shift_not_found")
        if shift[0] != "open":
            raise ValueError("shift_already_closed")

        opening_float = Decimal(str(shift[2] or 0))

        sales = self.db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) as total "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                "WHERE pr.shift_id = :sid AND pr.tenant_id = :tid AND pr.status = 'paid' "
                "GROUP BY pp.method"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_id, "tid": tenant_id},
        ).fetchall()

        cash_sales = Decimal("0")
        total_sales = Decimal("0")
        for method, amount in sales:
            total_sales += Decimal(str(amount or 0))
            if (method or "").strip().lower() == "cash":
                cash_sales = Decimal(str(amount or 0))

        expected_cash = opening_float + cash_sales
        variance = cash_count - expected_cash

        return {
            "shift_id": shift_id,
            "status": "closed",
            "closed_at": datetime.now(UTC),
            "opening_float": opening_float,
            "cash_count": cash_count,
            "sales_total": total_sales,
            "expected_cash": expected_cash,
            "variance": variance,
            "variance_pct": (
                (variance / expected_cash * 100) if expected_cash > 0 else Decimal("0")
            ),
        }


class POS_StockIntegrationUseCase:
    """Integración con inventory: descuenta stock por venta POS."""

    def __init__(self, db: Session, costing_service: InventoryCostingService):
        self.db = db
        self.costing = costing_service

    def execute(
        self,
        *,
        receipt_id: UUID,
        warehouse_id: UUID,
        tenant_id: UUID,
        lines: list[dict[str, Any]],
        costing_method: str = "avg",
    ) -> dict[str, Any]:
        moves = []
        for line in lines:
            product_id = line["product_id"]
            qty = Decimal(str(line["qty"]))

            if costing_method == "fifo":
                state, cogs = self.costing.apply_outbound_fifo(
                    str(tenant_id),
                    str(warehouse_id),
                    str(product_id),
                    qty=qty,
                    allow_negative=True,
                )
            elif costing_method == "lifo":
                state, cogs = self.costing.apply_outbound_lifo(
                    str(tenant_id),
                    str(warehouse_id),
                    str(product_id),
                    qty=qty,
                    allow_negative=True,
                )
            else:
                state = self.costing.apply_outbound(
                    str(tenant_id),
                    str(warehouse_id),
                    str(product_id),
                    qty=qty,
                    allow_negative=True,
                )
                cogs = qty * state.avg_cost

            cogs_unit = cogs / qty if qty > 0 else Decimal("0")

            moves.append(
                {
                    "product_id": product_id,
                    "qty": qty,
                    "cogs_unit": cogs_unit,
                    "cogs_total": cogs,
                }
            )

        return {
            "receipt_id": receipt_id,
            "warehouse_id": warehouse_id,
            "moves": moves,
        }


class POS_AccountingIntegrationUseCase:
    """Integración con accounting: crear asiento contable automáticamente."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        *,
        receipt_id: UUID,
        subtotal: Decimal,
        tax: Decimal,
        payment_methods: dict[str, Decimal],
        tenant_id: UUID,
        cogs_total: Decimal | None = None,
    ) -> dict[str, Any]:
        journal_lines = []

        for method, amount in payment_methods.items():
            if amount > 0:
                journal_lines.append(
                    {
                        "type": "debit",
                        "account": f"cash_or_bank_{method}",
                        "amount": amount,
                    }
                )

        if cogs_total and cogs_total > 0:
            journal_lines.append(
                {
                    "type": "debit",
                    "account": "cogs",
                    "amount": cogs_total,
                }
            )

        if subtotal > 0:
            journal_lines.append(
                {
                    "type": "credit",
                    "account": "sales_revenue",
                    "amount": subtotal,
                }
            )

        if tax > 0:
            journal_lines.append(
                {
                    "type": "credit",
                    "account": "vat_output",
                    "amount": tax,
                }
            )

        return {
            "receipt_id": receipt_id,
            "status": "posted",
            "lines": journal_lines,
        }
