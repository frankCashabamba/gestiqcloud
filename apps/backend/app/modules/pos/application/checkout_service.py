"""
POS Checkout Service — lógica de negocio del checkout extraída de receipts.py.

Responsabilidades:
1. Validar recibo y bloquearlo (FOR UPDATE)
2. Registrar pagos
3. Calcular totales con IVA
4. Resolver almacén
5. Descontar stock por línea (FIFO/LIFO/AVG) con soporte de lotes
6. Actualizar estado del recibo a 'paid'
7. Crear documentos complementarios (factura, venta) — best-effort
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.services.inventory_costing import InventoryCostingService

logger = logging.getLogger(__name__)


@dataclass
class PaymentIn:
    method: str
    amount: Decimal
    ref: str | None = None


@dataclass
class StockAllocationIn:
    line_id: UUID
    allocations: list[dict]  # [{lot, expires_at, qty}]


@dataclass
class CheckoutRequest:
    receipt_id: UUID
    tenant_id: UUID
    payments: list[PaymentIn]
    warehouse_id: UUID | None = None
    stock_selections: list[StockAllocationIn] = field(default_factory=list)
    invoice_series: str = "A"


@dataclass
class CheckoutResult:
    receipt_id: UUID
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    paid: Decimal
    change: Decimal
    documents_created: dict = field(default_factory=dict)


class CheckoutService:
    """
    Encapsula toda la lógica de negocio del checkout POS.
    El HTTP handler solo valida entrada, llama a execute() y formatea la respuesta.
    """

    def __init__(self, db: Session):
        self.db = db
        self._costing = InventoryCostingService(db)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def execute(self, req: CheckoutRequest) -> CheckoutResult:
        """
        Ejecuta el checkout de forma atómica:
        1. Valida recibo (FOR UPDATE)
        2. Registra pagos
        3. Calcula totales + IVA
        4. Resuelve almacén
        5. Descuenta stock por línea
        6. Marca recibo como 'paid'
        7. Crea documentos complementarios (best-effort)
        """
        self._validate_receipt(req.receipt_id, req.tenant_id)
        self._insert_payments(req.receipt_id, req.payments)
        subtotal, tax = self._calculate_totals(req.receipt_id)
        paid = sum(p.amount for p in req.payments)
        total = subtotal + tax

        if int(paid * 100) < int(total * 100):
            raise ValueError(
                f"insufficient_payment: received={float(paid):.2f} required={float(total):.2f}"
            )

        warehouse_id = self._resolve_warehouse(req.warehouse_id)
        self._process_stock_lines(req.receipt_id, req.tenant_id, warehouse_id, req.stock_selections)
        self._mark_paid(req.receipt_id, req.tenant_id, subtotal, tax, warehouse_id)
        self.db.commit()

        documents = self._create_documents(req.receipt_id, req.tenant_id, req.invoice_series)

        return CheckoutResult(
            receipt_id=req.receipt_id,
            subtotal=subtotal,
            tax=tax,
            total=total,
            paid=paid,
            change=paid - total,
            documents_created=documents,
        )

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _validate_receipt(self, receipt_id: UUID, tenant_id: UUID) -> None:
        row = self.db.execute(
            text(
                "SELECT shift_id, status FROM pos_receipts "
                "WHERE id = :id AND tenant_id = :tid FOR UPDATE"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_id, "tid": tenant_id},
        ).first()

        if not row:
            raise ValueError("receipt_not_found")
        if row[1] != "draft":
            raise ValueError(f"invalid_status:{row[1]}")

    def _insert_payments(self, receipt_id: UUID, payments: list[PaymentIn]) -> None:
        for payment in payments:
            self.db.execute(
                text(
                    "INSERT INTO pos_payments(id, receipt_id, method, amount, ref, paid_at) "
                    "VALUES (:id, :rid, :m, :a, :ref, :paid_at)"
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": uuid4(),
                    "rid": receipt_id,
                    "m": payment.method,
                    "a": float(payment.amount),
                    "ref": payment.ref,
                    "paid_at": datetime.now(UTC),
                },
            )

    def _calculate_totals(self, receipt_id: UUID) -> tuple[Decimal, Decimal]:
        row = self.db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100)), 0) AS subtotal, "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100) * rl.tax_rate), 0) AS tax "
                "FROM pos_receipt_lines rl WHERE rl.receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_id},
        ).first()

        subtotal = Decimal(str(row[0] or 0))
        tax = Decimal(str(row[1] or 0))

        # Respect tenant tax config
        tax_enabled = self._is_tax_enabled()
        default_tax = self._resolve_default_tax_rate()
        if not tax_enabled or (default_tax is not None and default_tax <= 0):
            tax = Decimal("0")

        return subtotal, tax

    def _is_tax_enabled(self) -> bool:
        from app.modules.pos.interface.http._deps import is_tax_enabled
        return is_tax_enabled(self.db)

    def _resolve_default_tax_rate(self) -> float | None:
        from app.modules.pos.interface.http._deps import resolve_default_tax_rate
        return resolve_default_tax_rate(self.db)

    def _resolve_warehouse(self, warehouse_id: UUID | None) -> UUID:
        if warehouse_id:
            return warehouse_id

        warehouses = self.db.execute(
            text("SELECT id FROM warehouses WHERE active = true LIMIT 2")
        ).fetchall()

        if len(warehouses) == 0:
            raise ValueError("no_active_warehouse")
        if len(warehouses) > 1:
            raise ValueError("multiple_warehouses_specify_id")
        return warehouses[0][0]

    def _process_stock_lines(
        self,
        receipt_id: UUID,
        tenant_id: UUID,
        warehouse_id: UUID,
        stock_selections: list[StockAllocationIn],
    ) -> None:
        from app.modules.pos.interface.http._deps import (
            ensure_generic_stock_row,
            load_locked_stock_rows,
            normalize_lot,
            resolve_inventory_costing_method,
            resolve_outbound_stock_fifo,
            resolve_selected_stock_row,
            sum_stock_rows_qty,
            to_decimal_q,
        )

        lines = self.db.execute(
            text(
                "SELECT id, product_id, qty, unit_price, discount_pct "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_id},
        ).fetchall()

        selection_map = {str(sel.line_id): sel for sel in stock_selections}
        costing_method = resolve_inventory_costing_method(self.db)

        for line in lines:
            line_id, product_id, qty_sold, unit_price, discount_pct = (
                line[0], line[1], float(line[2]), float(line[3]), float(line[4] or 0)
            )
            self._process_line(
                line_id=line_id,
                product_id=product_id,
                qty_sold=qty_sold,
                unit_price=unit_price,
                discount_pct=discount_pct,
                tenant_id=tenant_id,
                warehouse_id=warehouse_id,
                receipt_id=receipt_id,
                costing_method=costing_method,
                line_selection=selection_map.get(str(line_id)),
                helpers={
                    "load_locked_stock_rows": load_locked_stock_rows,
                    "ensure_generic_stock_row": ensure_generic_stock_row,
                    "resolve_selected_stock_row": resolve_selected_stock_row,
                    "resolve_outbound_stock_fifo": resolve_outbound_stock_fifo,
                    "sum_stock_rows_qty": sum_stock_rows_qty,
                    "normalize_lot": normalize_lot,
                    "to_decimal_q": to_decimal_q,
                },
            )

    def _process_line(
        self,
        *,
        line_id,
        product_id,
        qty_sold: float,
        unit_price: float,
        discount_pct: float,
        tenant_id: UUID,
        warehouse_id: UUID,
        receipt_id: UUID,
        costing_method: str,
        line_selection,
        helpers: dict,
    ) -> None:
        load_locked = helpers["load_locked_stock_rows"]
        ensure_generic = helpers["ensure_generic_stock_row"]
        resolve_selected = helpers["resolve_selected_stock_row"]
        resolve_fifo = helpers["resolve_outbound_stock_fifo"]
        sum_qty = helpers["sum_stock_rows_qty"]
        normalize_lot = helpers["normalize_lot"]
        to_dec = helpers["to_decimal_q"]

        stock_rows = load_locked(self.db, warehouse_id, product_id)
        allocations: list[tuple] = []

        if line_selection is not None:
            selected_total = 0.0
            for alloc in line_selection.allocations:
                alloc_qty = float(alloc.get("qty") or 0)
                if alloc_qty <= 0:
                    continue
                stock_item = resolve_selected(
                    stock_rows,
                    lot=alloc.get("lot"),
                    expires_at=alloc.get("expires_at"),
                )
                if float(stock_item[1] or 0) < alloc_qty:
                    raise ValueError("selected_lot_insufficient")
                allocations.append((
                    stock_item, alloc_qty,
                    normalize_lot(alloc.get("lot")),
                    alloc.get("expires_at"),
                ))
                selected_total += alloc_qty
            if abs(selected_total - qty_sold) > 0.000001:
                raise ValueError("invalid_lot_allocation_total")
        else:
            fifo_allocs, remaining = resolve_fifo(stock_rows, qty_sold)
            if remaining > 0.000001 or not fifo_allocs:
                stock_item = ensure_generic(
                    self.db,
                    tenant_id=tenant_id,
                    warehouse_id=warehouse_id,
                    product_id=product_id,
                )
                stock_rows = [stock_item]
                allocations.append((stock_item, qty_sold, None, None))
            else:
                for si, aq, lot, exp in fifo_allocs:
                    allocations.append((si, aq, lot, exp))

        current_qty = sum_qty(stock_rows)
        cost_price = self.db.execute(
            text("SELECT cost_price FROM products WHERE id = :pid"),
            {"pid": product_id},
        ).scalar()
        fallback_cost = to_dec(float(cost_price or 0), "0.000001")
        qty_dec = to_dec(qty_sold, "0.000001")

        # Costing: FIFO / LIFO / AVG
        if costing_method == "fifo":
            cogs_total = to_dec(0, "0.000001")
            for si, alloc_qty, lot, exp in allocations:
                _, alloc_cogs = self._costing.apply_outbound_fifo(
                    str(tenant_id), str(warehouse_id), str(product_id),
                    qty=to_dec(alloc_qty, "0.000001"),
                    allow_negative=False, lot=lot, expires_at=exp,
                )
                cogs_total += alloc_cogs
        elif costing_method == "lifo":
            cogs_total = to_dec(0, "0.000001")
            for si, alloc_qty, lot, exp in allocations:
                _, alloc_cogs = self._costing.apply_outbound_lifo(
                    str(tenant_id), str(warehouse_id), str(product_id),
                    qty=to_dec(alloc_qty, "0.000001"),
                    allow_negative=False, lot=lot, expires_at=exp,
                )
                cogs_total += alloc_cogs
        else:  # avg
            _state = self._costing.apply_outbound(
                str(tenant_id), str(warehouse_id), str(product_id),
                qty=qty_dec, allow_negative=False,
                initial_qty=to_dec(current_qty, "0.000001"),
                initial_avg_cost=fallback_cost,
            )
            cogs_total = qty_dec * _state.avg_cost

        cogs_unit = to_dec(cogs_total / qty_dec, "0.000001") if qty_dec > 0 else to_dec(0, "0.000001")

        net_total = to_dec(qty_sold, "0.000001") * to_dec(unit_price, "0.0001")
        net_total = net_total * (Decimal("1") - (to_dec(discount_pct, "0.01") / 100))
        net_total = to_dec(net_total, "0.01")
        cogs_money = to_dec(cogs_total, "0.01")
        gross_profit = to_dec(net_total - cogs_money, "0.01")
        gross_margin = to_dec(gross_profit / net_total, "0.0001") if net_total > 0 else to_dec(0, "0.0001")

        self.db.execute(
            text(
                "UPDATE pos_receipt_lines "
                "SET net_total = :net, cogs_unit = :cu, cogs_total = :ct, "
                "gross_profit = :gp, gross_margin_pct = :gmp WHERE id = :id"
            ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
            {"id": line_id, "net": float(net_total), "cu": float(cogs_unit),
             "ct": float(cogs_money), "gp": float(gross_profit), "gmp": float(gross_margin)},
        )

        if current_qty - qty_sold < 0:
            raise ValueError("insufficient_stock")

        # Apply stock deductions
        running_total = 0.0
        for si, alloc_qty, lot, exp in allocations:
            new_qty = float(si[1] or 0) - alloc_qty
            if new_qty < 0:
                raise ValueError("selected_lot_insufficient")
            running_total += alloc_qty
            alloc_dec = to_dec(alloc_qty, "0.000001")
            alloc_ratio = alloc_dec / qty_dec if qty_dec > 0 else to_dec(0, "0.000001")
            alloc_cost = to_dec(cogs_money * alloc_ratio, "0.01")

            self.db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, "
                    "tentative, posted, lot, expires_at, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'sale', 'pos_receipt', :rid, "
                    "FALSE, TRUE, :lot, :exp, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id, "pid": product_id, "wid": warehouse_id,
                    "q": alloc_qty, "rid": receipt_id,
                    "lot": lot, "exp": exp,
                    "uc": float(cogs_unit), "tc": float(alloc_cost),
                    "occurred_at": datetime.now(UTC),
                },
            )
            self.db.execute(
                text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"q": new_qty, "id": si[0]},
            )

        if abs(running_total - qty_sold) > 0.000001:
            raise ValueError("invalid_lot_allocation_total")

    def _mark_paid(
        self,
        receipt_id: UUID,
        tenant_id: UUID,
        subtotal: Decimal,
        tax: Decimal,
        warehouse_id: UUID,
    ) -> None:
        total = subtotal + tax
        self.db.execute(
            text(
                "UPDATE pos_receipts "
                "SET status = 'paid', gross_total = :gt, tax_total = :tt, "
                "warehouse_id = :wid, paid_at = NOW() "
                "WHERE id = :id AND tenant_id = :tid"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("wid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_id, "tid": tenant_id, "gt": float(total), "tt": float(tax), "wid": warehouse_id},
        )

    def _create_documents(
        self, receipt_id: UUID, tenant_id: UUID, invoice_series: str
    ) -> dict:
        """Crea documentos complementarios (factura, venta). Best-effort — no aborta el pago."""
        documents: dict = {}
        try:
            from app.modules.pos.application.invoice_integration import POSInvoicingService

            service = POSInvoicingService(self.db, tenant_id)

            try:
                inv = service.create_invoice_from_receipt(
                    receipt_id, customer_id=None, invoice_series=invoice_series
                )
                if inv:
                    documents["invoice"] = inv
                    self.db.commit()
                else:
                    self.db.rollback()
            except Exception as e:
                logger.warning("Error creating invoice from receipt: %s", e)
                try:
                    self.db.rollback()
                except Exception:
                    pass

            try:
                sale = service.create_sale_from_receipt(receipt_id)
                if sale:
                    documents["sale"] = sale
                    self.db.commit()
                else:
                    self.db.rollback()
            except Exception as e:
                logger.warning("Error creating sale from receipt: %s", e)
                try:
                    self.db.rollback()
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Error creating complementary documents: %s", e)

        return documents
