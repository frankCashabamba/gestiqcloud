"""POS — Router de recibos (receipts)."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.audit_events import audit_event
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.services.inventory_costing import InventoryCostingService

from ._deps import (
    CalculateTotalsIn,
    CalculateTotalsOut,
    CheckoutIn,
    ReceiptCreateIn,
    RefundReceiptIn,
    ensure_generic_stock_row,
    get_claims,
    get_tenant_id,
    get_user_id,
    is_company_admin,
    is_tax_enabled,
    load_locked_stock_rows,
    normalize_lot,
    resolve_default_tax_rate,
    resolve_inventory_costing_method,
    resolve_outbound_stock_fifo,
    resolve_selected_stock_row,
    sum_stock_rows_qty,
    to_decimal,
    to_decimal_q,
    validate_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Receipts"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# CALCULATE TOTALS (sin persistir)
# ============================================================================


@router.post(
    "/receipts/calculate_totals",
    response_model=CalculateTotalsOut,
    dependencies=[Depends(require_permission("pos.receipt.create"))],
)
def calculate_receipt_totals(payload: CalculateTotalsIn):
    """Calcula totales de un recibo sin persistirlo. Usa Decimal para precisión."""
    if not payload.lines:
        return CalculateTotalsOut(
            subtotal=0.0,
            line_discounts=0.0,
            global_discount=0.0,
            base_after_discounts=0.0,
            tax=0.0,
            total=0.0,
        )

    subtotal = Decimal("0")
    line_discounts = Decimal("0")
    tax_total = Decimal("0")

    for line in payload.lines:
        raw_qty = Decimal(str(line.qty))
        raw_price = Decimal(str(line.unit_price))
        line_subtotal = to_decimal_q(raw_qty * raw_price, "0.01")
        subtotal += line_subtotal

        line_discount = to_decimal_q(
            line_subtotal * (Decimal(str(line.discount_pct)) / Decimal("100")), "0.01"
        )
        line_discounts += line_discount

        line_net = line_subtotal - line_discount
        line_tax = to_decimal_q(line_net * Decimal(str(line.tax_rate)), "0.01")
        tax_total += line_tax

    base_after_line_discounts = subtotal - line_discounts
    global_discount = to_decimal_q(
        base_after_line_discounts * (Decimal(str(payload.global_discount_pct)) / Decimal("100")),
        "0.01",
    )
    base_after_all_discounts = base_after_line_discounts - global_discount
    total = base_after_all_discounts + tax_total

    return CalculateTotalsOut(
        subtotal=float(subtotal),
        line_discounts=float(line_discounts),
        global_discount=float(global_discount),
        base_after_discounts=float(base_after_all_discounts),
        tax=float(tax_total),
        total=float(total),
    )


# ============================================================================
# CREATE
# ============================================================================


@router.post(
    "/receipts",
    response_model=dict,
    status_code=201,
    dependencies=[Depends(require_permission("pos.receipt.create"))],
)
def create_receipt(payload: ReceiptCreateIn, request: Request, db: Session = Depends(get_db)):
    """Crea un nuevo recibo POS en estado draft."""
    ensure_guc_from_request(request, db, persist=True)

    claims = get_claims(request)
    tenant_id = get_tenant_id(request)
    current_user_id = get_user_id(request)
    shift_uuid = validate_uuid(payload.shift_id, "Shift ID")
    register_uuid = validate_uuid(payload.register_id, "Register ID")
    customer_uuid = (
        validate_uuid(payload.customer_id, "Customer ID") if payload.customer_id else None
    )

    try:
        # Resolver cajero (admin puede asignar a otro)
        cashier_id = current_user_id
        if payload.cashier_id:
            requested_cashier_id = validate_uuid(payload.cashier_id, "Cashier ID")
            if requested_cashier_id != current_user_id and not is_company_admin(claims):
                raise HTTPException(status_code=403, detail="cashier_override_forbidden")
            exists = db.execute(
                text(
                    "SELECT 1 FROM company_users WHERE id = :cid AND tenant_id = :tid AND is_active = TRUE"
                ).bindparams(
                    bindparam("cid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"cid": requested_cashier_id, "tid": tenant_id},
            ).first()
            if not exists:
                raise HTTPException(status_code=400, detail="cashier_not_found")
            cashier_id = requested_cashier_id

        if customer_uuid:
            exists = db.execute(
                text("SELECT 1 FROM clients WHERE id = :cid AND tenant_id = :tid").bindparams(
                    bindparam("cid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"cid": customer_uuid, "tid": tenant_id},
            ).first()
            if not exists:
                raise HTTPException(status_code=400, detail="customer_not_found")

        shift = db.execute(
            text("SELECT status FROM pos_shifts WHERE id = :sid AND register_id = :rid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "rid": register_uuid},
        ).first()

        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")
        if shift[0] != "open":
            raise HTTPException(status_code=400, detail="El turno no está abierto")

        # Numeración atómica con advisory lock
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"{tenant_id}-{register_uuid}-POS_R"},
        )

        ticket_number = db.execute(
            text(
                "SELECT COALESCE(MAX("
                "CASE WHEN SPLIT_PART(number, '-', 2) ~ '^[0-9]+$' "
                "THEN (SPLIT_PART(number, '-', 2))::int ELSE 0 END"
                "), 0) + 1 "
                "FROM pos_receipts WHERE tenant_id = :tid AND register_id = :rid"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
            ),
            {"tid": tenant_id, "rid": register_uuid},
        ).scalar()
        ticket_number = f"R-{ticket_number:04d}"

        from ._deps import resolve_tenant_currency

        currency = resolve_tenant_currency(db, tenant_id)

        row = db.execute(
            text(
                "INSERT INTO pos_receipts("
                "tenant_id, register_id, shift_id, cashier_id, customer_id, number, status, "
                "gross_total, tax_total, currency, created_at"
                ") VALUES ("
                ":tid, :rid, :sid, :cashier_id, :customer_id, :number, 'draft', "
                "0, 0, :currency, NOW()"
                ") RETURNING id"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("cashier_id", type_=PGUUID(as_uuid=True)),
                bindparam("customer_id", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "rid": register_uuid,
                "sid": shift_uuid,
                "cashier_id": cashier_id,
                "customer_id": customer_uuid,
                "number": ticket_number,
                "currency": currency,
            },
        ).first()

        receipt_id = row[0]
        db.commit()

        # Restaurar contexto RLS tras commit
        ensure_guc_from_request(request, db, persist=True)

        tax_enabled = is_tax_enabled(db)
        default_tax = resolve_default_tax_rate(db)

        for line in payload.lines:
            product_uuid = validate_uuid(line.product_id, "Product ID")

            tax_rate = line.tax_rate
            if not tax_enabled:
                tax_rate = 0.0
            else:
                if tax_rate is None and default_tax is not None:
                    tax_rate = max(default_tax, 0.0)
                if tax_rate is None:
                    tax_rate = 0.0
                elif tax_rate > 1:
                    tax_rate = tax_rate / 100.0
                elif tax_rate < 0:
                    tax_rate = 0.0

            qty_sold = abs(float(line.qty or 0))
            unit_price = float(line.unit_price or 0)
            discount_pct = float(line.discount_pct or 0)
            net_total = to_decimal_q(qty_sold, "0.000001") * to_decimal_q(unit_price, "0.0001")
            net_total = net_total * (Decimal("1") - (to_decimal_q(discount_pct, "0.01") / 100))
            net_total = to_decimal_q(net_total, "0.01")
            line_tax = to_decimal_q(net_total * Decimal(str(tax_rate)), "0.01")
            line_total = to_decimal_q(net_total + line_tax, "0.01")

            db.execute(
                text(
                    "INSERT INTO pos_receipt_lines("
                    "receipt_id, product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                    "uom, net_total, cogs_unit, cogs_total, gross_profit, gross_margin_pct"
                    ") VALUES ("
                    ":receipt_id, :product_id, :qty, :unit_price, :tax_rate, :discount_pct, :line_total, "
                    ":uom, :net_total, 0, 0, 0, 0"
                    ")"
                ).bindparams(
                    bindparam("receipt_id", type_=PGUUID(as_uuid=True)),
                    bindparam("product_id", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "receipt_id": receipt_id,
                    "product_id": product_uuid,
                    "qty": qty_sold,
                    "unit_price": unit_price,
                    "tax_rate": tax_rate,
                    "discount_pct": discount_pct,
                    "line_total": float(line_total),
                    "uom": line.uom,
                    "net_total": float(net_total),
                },
            )

        db.commit()
        return {"id": str(receipt_id), "number": ticket_number}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error al crear recibo")
        raise HTTPException(status_code=500, detail=f"Error al crear recibo: {str(e)}")


# ============================================================================
# LIST / GET / DELETE
# ============================================================================


@router.get(
    "/receipts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def list_receipts(
    request: Request,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    shift_id: str | None = None,
    cashier_id: str | None = None,
    limit: int = Query(default=500, le=1000),
    db: Session = Depends(get_db),
):
    """Lista recibos con filtros opcionales."""
    ensure_guc_from_request(request, db, persist=True)
    tenant_id = get_tenant_id(request)

    sql_parts = [
        "SELECT r.id, r.shift_id, r.register_id, r.cashier_id, r.number, r.status, "
        "r.gross_total, r.tax_total, r.created_at, r.paid_at, "
        "u.first_name, u.last_name, u.username, u.email "
        "FROM pos_receipts r "
        "LEFT JOIN company_users u ON u.id = r.cashier_id "
        "WHERE r.tenant_id = :tid"
    ]
    params: dict = {"tid": tenant_id}

    if status:
        sql_parts.append("AND status = :st")
        params["st"] = status
    if shift_id:
        shift_uuid = validate_uuid(shift_id, "Shift ID")
        sql_parts.append("AND shift_id = :sid")
        params["sid"] = shift_uuid
    if cashier_id:
        cashier_uuid = validate_uuid(cashier_id, "Cashier ID")
        sql_parts.append("AND cashier_id = :cid")
        params["cid"] = cashier_uuid
    if since:
        sql_parts.append("AND created_at >= :since")
        params["since"] = since
    if until:
        sql_parts.append("AND created_at <= :until")
        params["until"] = until

    sql_parts.append(f"ORDER BY created_at DESC LIMIT {min(limit, 1000)}")

    try:
        rows = db.execute(text(" ".join(sql_parts)), params).fetchall()
        return [
            {
                "id": str(r[0]),
                "shift_id": str(r[1]),
                "register_id": str(r[2]),
                "cashier_id": str(r[3]) if r[3] else None,
                "number": r[4],
                "status": r[5],
                "gross_total": float(r[6]) if r[6] else 0,
                "tax_total": float(r[7]) if r[7] else 0,
                "created_at": r[8].isoformat() if r[8] else None,
                "paid_at": r[9].isoformat() if r[9] else None,
                "cashier_name": (
                    f"{r[10]} {r[11]}".strip() if r[10] or r[11] else (r[12] or r[13])
                ),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar recibos: {str(e)}")


@router.get(
    "/receipts/{receipt_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def get_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene un recibo con sus líneas y pagos."""
    ensure_guc_from_request(request, db, persist=True)
    rid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    try:
        rec = db.execute(
            text(
                "SELECT r.id, r.tenant_id, r.register_id, r.shift_id, r.number, r.status, r.gross_total, "
                "r.tax_total, r.currency, r.customer_id, r.invoice_id, r.created_at, r.paid_at, r.cashier_id, "
                "u.first_name, u.last_name, u.username, u.email "
                "FROM pos_receipts r "
                "LEFT JOIN company_users u ON u.id = r.cashier_id "
                "WHERE r.id = :id AND r.tenant_id = :tid"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": rid, "tid": tenant_id},
        ).first()

        if not rec:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        lines = db.execute(
            text(
                "SELECT rl.id, rl.product_id, p.name, p.sku, rl.qty, rl.uom, rl.unit_price, "
                "rl.tax_rate, rl.discount_pct, rl.line_total "
                "FROM pos_receipt_lines rl "
                "LEFT JOIN products p ON p.id = rl.product_id "
                "WHERE rl.receipt_id = :rid ORDER BY rl.id"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": rid},
        ).fetchall()

        payments = db.execute(
            text(
                "SELECT id, method, amount, ref, paid_at "
                "FROM pos_payments WHERE receipt_id = :rid ORDER BY paid_at"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": rid},
        ).fetchall()

        return {
            "id": str(rec[0]),
            "tenant_id": str(rec[1]) if rec[1] else None,
            "register_id": str(rec[2]) if rec[2] else None,
            "shift_id": str(rec[3]) if rec[3] else None,
            "number": rec[4],
            "status": rec[5],
            "gross_total": float(rec[6] or 0),
            "tax_total": float(rec[7] or 0),
            "currency": rec[8],
            "customer_id": str(rec[9]) if rec[9] else None,
            "invoice_id": str(rec[10]) if rec[10] else None,
            "created_at": rec[11].isoformat() if rec[11] else None,
            "paid_at": rec[12].isoformat() if rec[12] else None,
            "cashier_id": str(rec[13]) if rec[13] else None,
            "cashier_name": (
                f"{rec[14]} {rec[15]}".strip() if rec[14] or rec[15] else (rec[16] or rec[17])
            ),
            "lines": [
                {
                    "id": str(ln[0]) if ln[0] else None,
                    "product_id": str(ln[1]) if ln[1] else None,
                    "product_name": ln[2],
                    "product_code": ln[3],
                    "qty": float(ln[4] or 0),
                    "uom": ln[5],
                    "unit_price": float(ln[6] or 0),
                    "tax_rate": float(ln[7] or 0),
                    "discount_pct": float(ln[8] or 0),
                    "line_total": float(ln[9] or 0),
                }
                for ln in lines
            ],
            "payments": [
                {
                    "id": str(p[0]) if p[0] else None,
                    "method": p[1],
                    "amount": float(p[2] or 0),
                    "ref": p[3],
                    "paid_at": p[4].isoformat() if p[4] else None,
                }
                for p in payments
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener recibo: {str(e)}")


@router.delete(
    "/receipts/{receipt_id}",
    status_code=204,
    dependencies=[Depends(require_permission("pos.receipt.manage"))],
)
def delete_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina un recibo en borrador o sin pagar."""
    ensure_guc_from_request(request, db, persist=True)
    rid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    try:
        row = db.execute(
            text("SELECT status FROM pos_receipts WHERE id = :id AND tenant_id = :tid").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": rid, "tid": tenant_id},
        ).first()

        if not row:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        if row[0] not in ("draft", "unpaid"):
            raise HTTPException(
                status_code=400, detail="Solo se pueden borrar recibos en borrador o sin pagar"
            )

        db.execute(
            text("DELETE FROM pos_payments WHERE receipt_id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        )
        db.execute(
            text("DELETE FROM pos_receipt_lines WHERE receipt_id = :id").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True))
            ),
            {"id": rid},
        )
        db.execute(
            text("DELETE FROM pos_receipts WHERE id = :id AND tenant_id = :tid").bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": rid, "tid": tenant_id},
        )
        db.commit()
        try:
            claims = get_claims(request)
            user_id = claims.get("user_id")
            audit_event(
                db,
                action="delete",
                entity_type="pos_receipt",
                entity_id=str(rid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={"status": row[0]},
                req=request,
            )
        except Exception:
            pass
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar recibo: {str(e)}")


# ============================================================================
# CHECKOUT
# ============================================================================


@router.post(
    "/receipts/{receipt_id}/checkout",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.pay"))],
)
def checkout(
    receipt_id: str,
    payload: CheckoutIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Registra pagos, descuenta stock y crea documentos complementarios."""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    try:
        receipt = db.execute(
            text(
                "SELECT shift_id, status FROM pos_receipts "
                "WHERE id = :id AND tenant_id = :tid FOR UPDATE"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_uuid, "tid": tenant_id},
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        if receipt[1] != "draft":
            raise HTTPException(
                status_code=400,
                detail=f"Recibo en estado '{receipt[1]}', debe estar en 'draft'",
            )

        for payment in payload.payments:
            db.execute(
                text(
                    "INSERT INTO pos_payments(id, receipt_id, method, amount, ref, paid_at) "
                    "VALUES (:id, :rid, :m, :a, :ref, :paid_at)"
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "id": uuid4(),
                    "rid": receipt_uuid,
                    "m": payment.method,
                    "a": payment.amount,
                    "ref": payment.ref,
                    "paid_at": datetime.utcnow(),
                },
            )

        totals = db.execute(
            text(
                "SELECT "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100)), 0) AS subtotal, "
                "COALESCE(SUM(ABS(rl.qty) * rl.unit_price * (1 - rl.discount_pct/100) * rl.tax_rate), 0) AS tax "
                "FROM pos_receipt_lines rl WHERE rl.receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        payments_total = db.execute(
            text(
                "SELECT COALESCE(SUM(amount), 0) FROM pos_payments WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()

        subtotal = to_decimal(float(totals[0] or 0))
        tax = to_decimal(float(totals[1] or 0))

        tax_enabled = is_tax_enabled(db)
        default_tax = resolve_default_tax_rate(db)
        if not tax_enabled or (default_tax is not None and default_tax <= 0):
            tax = to_decimal(0.0)

        total = subtotal + tax
        paid = to_decimal(float(payments_total[0] or 0))

        if int(paid * 100) < int(total * 100):
            raise HTTPException(
                status_code=400,
                detail=f"Pago insuficiente. Recibido: ${paid:.2f}, Requerido: ${total:.2f}",
            )

        warehouse_id = payload.warehouse_id
        if warehouse_id:
            warehouse_uuid = validate_uuid(warehouse_id, "Warehouse ID")
        else:
            warehouses = db.execute(
                text("SELECT id FROM warehouses WHERE active = true LIMIT 2")
            ).fetchall()
            if len(warehouses) == 0:
                raise HTTPException(status_code=400, detail="No hay almacenes activos disponibles")
            if len(warehouses) > 1:
                raise HTTPException(
                    status_code=400,
                    detail="Múltiples almacenes disponibles, debe especificar warehouse_id",
                )
            warehouse_uuid = warehouses[0][0]

        lines = db.execute(
            text(
                "SELECT id, product_id, qty, unit_price, discount_pct "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        line_selection_map = {str(sel.line_id): sel for sel in (payload.stock_selections or [])}
        costing = InventoryCostingService(db)
        costing_method = resolve_inventory_costing_method(db)

        for line in lines:
            line_id = line[0]
            product_id = line[1]
            qty_sold = float(line[2])
            unit_price = float(line[3])
            discount_pct = float(line[4] or 0)

            stock_rows = load_locked_stock_rows(db, warehouse_uuid, product_id)
            line_selection = line_selection_map.get(str(line_id))
            allocations: list[tuple] = []

            if line_selection is not None:
                selected_total = 0.0
                for allocation in line_selection.allocations:
                    alloc_qty = float(allocation.qty or 0)
                    if alloc_qty <= 0:
                        continue
                    stock_item = resolve_selected_stock_row(
                        stock_rows, lot=allocation.lot, expires_at=allocation.expires_at
                    )
                    if float(stock_item[1] or 0) < alloc_qty:
                        raise HTTPException(status_code=400, detail="selected_lot_insufficient")
                    allocations.append(
                        (
                            stock_item,
                            alloc_qty,
                            normalize_lot(allocation.lot),
                            allocation.expires_at,
                        )
                    )
                    selected_total += alloc_qty
                if abs(selected_total - qty_sold) > 0.000001:
                    raise HTTPException(status_code=400, detail="invalid_lot_allocation_total")
            else:
                fifo_allocs, remaining = resolve_outbound_stock_fifo(stock_rows, qty_sold)
                if remaining > 0.000001 or not fifo_allocs:
                    # Sin stock suficiente → fallback a fila genérica (permite negativo)
                    stock_item = ensure_generic_stock_row(
                        db,
                        tenant_id=tenant_id,
                        warehouse_id=warehouse_uuid,
                        product_id=product_id,
                    )
                    stock_rows = [stock_item]
                    allocations.append((stock_item, qty_sold, None, None))
                else:
                    for si, alloc_qty, lot, exp in fifo_allocs:
                        allocations.append((si, alloc_qty, lot, exp))

            current_qty = sum_stock_rows_qty(stock_rows)

            cost_price = db.execute(
                text("SELECT cost_price FROM products WHERE id = :pid"),
                {"pid": product_id},
            ).scalar()
            fallback_cost = to_decimal_q(float(cost_price or 0), "0.000001")

            db.execute(
                text(
                    "INSERT INTO inventory_cost_state(tenant_id, warehouse_id, product_id, on_hand_qty, avg_cost) "
                    "VALUES (:tid, :wid, :pid, :q, :avg) "
                    "ON CONFLICT (tenant_id, warehouse_id, product_id) "
                    "DO UPDATE SET on_hand_qty = EXCLUDED.on_hand_qty"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "wid": warehouse_uuid,
                    "pid": product_id,
                    "q": float(current_qty),
                    "avg": float(fallback_cost),
                },
            )

            qty_dec = to_decimal_q(qty_sold, "0.000001")

            if costing_method == "fifo":
                cogs_total = to_decimal_q(0, "0.000001")
                for si, alloc_qty, lot, exp in allocations:
                    _, alloc_cogs = costing.apply_outbound_fifo(
                        str(tenant_id),
                        str(warehouse_uuid),
                        str(product_id),
                        qty=to_decimal_q(alloc_qty, "0.000001"),
                        allow_negative=False,
                        lot=lot,
                        expires_at=exp,
                    )
                    cogs_total += alloc_cogs
                cogs_unit = (
                    to_decimal_q(cogs_total / qty_dec, "0.000001")
                    if qty_dec > 0
                    else to_decimal_q(0, "0.000001")
                )
            elif costing_method == "lifo":
                cogs_total = to_decimal_q(0, "0.000001")
                for si, alloc_qty, lot, exp in allocations:
                    _, alloc_cogs = costing.apply_outbound_lifo(
                        str(tenant_id),
                        str(warehouse_uuid),
                        str(product_id),
                        qty=to_decimal_q(alloc_qty, "0.000001"),
                        allow_negative=False,
                        lot=lot,
                        expires_at=exp,
                    )
                    cogs_total += alloc_cogs
                cogs_unit = (
                    to_decimal_q(cogs_total / qty_dec, "0.000001")
                    if qty_dec > 0
                    else to_decimal_q(0, "0.000001")
                )
            else:
                _state = costing.apply_outbound(
                    str(tenant_id),
                    str(warehouse_uuid),
                    str(product_id),
                    qty=qty_dec,
                    allow_negative=False,
                    initial_qty=to_decimal_q(current_qty, "0.000001"),
                    initial_avg_cost=fallback_cost,
                )
                cogs_unit = _state.avg_cost
                cogs_total = qty_dec * cogs_unit

            net_total = to_decimal_q(qty_sold, "0.000001") * to_decimal_q(unit_price, "0.0001")
            net_total = net_total * (Decimal("1") - (to_decimal_q(discount_pct, "0.01") / 100))
            net_total = to_decimal_q(net_total, "0.01")
            cogs_total_money = to_decimal_q(cogs_total, "0.01")
            gross_profit = to_decimal_q(net_total - cogs_total_money, "0.01")
            gross_margin_pct = (
                to_decimal_q(gross_profit / net_total, "0.0001")
                if net_total > 0
                else to_decimal_q(0, "0.0001")
            )

            db.execute(
                text(
                    "UPDATE pos_receipt_lines "
                    "SET net_total = :net, cogs_unit = :cu, cogs_total = :ct, "
                    "gross_profit = :gp, gross_margin_pct = :gmp "
                    "WHERE id = :id"
                ).bindparams(bindparam("id", type_=PGUUID(as_uuid=True))),
                {
                    "id": line_id,
                    "net": float(net_total),
                    "cu": float(cogs_unit),
                    "ct": float(cogs_total_money),
                    "gp": float(gross_profit),
                    "gmp": float(gross_margin_pct),
                },
            )

            if current_qty - qty_sold < 0:
                raise HTTPException(status_code=400, detail="insufficient_stock")

            running_total = 0.0
            for si, alloc_qty, selected_lot, selected_exp in allocations:
                selected_qty = float(si[1] or 0)
                new_qty = selected_qty - alloc_qty
                if new_qty < 0:
                    raise HTTPException(status_code=400, detail="selected_lot_insufficient")
                running_total += alloc_qty
                alloc_qty_dec = to_decimal_q(alloc_qty, "0.000001")
                alloc_ratio = (
                    alloc_qty_dec / qty_dec if qty_dec > 0 else to_decimal_q(0, "0.000001")
                )
                alloc_total_cost = to_decimal_q(cogs_total_money * alloc_ratio, "0.01")

                db.execute(
                    text(
                        "INSERT INTO stock_moves("
                        "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, "
                        "tentative, posted, lot, expires_at, unit_cost, total_cost, occurred_at"
                        ") VALUES ("
                        ":tid, :pid, :wid, :q, 'sale', 'pos_receipt', :rid, FALSE, TRUE, "
                        ":lot, :exp, :uc, :tc, :occurred_at"
                        ")"
                    ).bindparams(
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                        bindparam("pid", type_=PGUUID(as_uuid=True)),
                        bindparam("wid", type_=PGUUID(as_uuid=True)),
                        bindparam("rid", type_=PGUUID(as_uuid=True)),
                    ),
                    {
                        "tid": tenant_id,
                        "pid": product_id,
                        "wid": warehouse_uuid,
                        "q": alloc_qty,
                        "rid": receipt_uuid,
                        "lot": selected_lot,
                        "exp": selected_exp,
                        "uc": float(cogs_unit),
                        "tc": float(alloc_total_cost),
                        "occurred_at": datetime.utcnow(),
                    },
                )
                db.execute(
                    text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                        bindparam("id", type_=PGUUID(as_uuid=True))
                    ),
                    {"q": new_qty, "id": si[0]},
                )

            if abs(running_total - qty_sold) > 0.000001:
                raise HTTPException(status_code=400, detail="invalid_lot_allocation_total")

        db.execute(
            text(
                "UPDATE pos_receipts "
                "SET status = 'paid', gross_total = :gt, tax_total = :tt, "
                "warehouse_id = :wid, paid_at = NOW() "
                "WHERE id = :id AND tenant_id = :tid"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_uuid, "tid": tenant_id, "gt": total, "tt": tax, "wid": warehouse_uuid},
        )
        db.commit()

        # Documentos complementarios (best-effort, no abortan el pago)
        documents_created: dict = {}
        try:
            from app.modules.pos.application.invoice_integration import POSInvoicingService

            service = POSInvoicingService(db, tenant_id)
            try:
                invoice_result = service.create_invoice_from_receipt(
                    receipt_uuid,
                    customer_id=None,
                    invoice_series=getattr(payload, "invoice_series", "A"),
                )
                if invoice_result:
                    documents_created["invoice"] = invoice_result
                    db.commit()
                else:
                    db.rollback()
            except Exception as e:
                logger.warning("Error creating invoice from receipt: %s", e)
                try:
                    db.rollback()
                except Exception:
                    pass
            try:
                sale_result = service.create_sale_from_receipt(receipt_uuid)
                if sale_result:
                    documents_created["sale"] = sale_result
                    db.commit()
                else:
                    db.rollback()
            except Exception as e:
                logger.warning("Error creating sale from receipt: %s", e)
                try:
                    db.rollback()
                except Exception:
                    pass
        except Exception as e:
            logger.warning("Error creating complementary documents: %s", e)

        try:
            claims = get_claims(request)
            user_id = claims.get("user_id")
            audit_event(
                db,
                action="issue",
                entity_type="pos_receipt",
                entity_id=str(receipt_uuid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={
                    "status": "paid",
                    "totals": {
                        "subtotal": float(subtotal),
                        "tax": float(tax),
                        "total": float(total),
                        "paid": float(paid),
                        "change": float(paid - total),
                    },
                    "documents_created": list(documents_created.keys()),
                },
                req=request,
            )
        except Exception:
            pass

        return {
            "ok": True,
            "receipt_id": str(receipt_uuid),
            "status": "paid",
            "totals": {
                "subtotal": float(subtotal),
                "tax": float(tax),
                "total": float(total),
                "paid": float(paid),
                "change": float(paid - total),
            },
            "documents_created": documents_created,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en checkout: {str(e)}")


# ============================================================================
# REFUND
# ============================================================================


@router.post(
    "/receipts/{receipt_id}/refund",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.refund"))],
)
def refund_receipt(
    receipt_id: str,
    payload: RefundReceiptIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Devolución total del recibo: líneas negativas y reposición de stock."""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    try:
        receipt = db.execute(
            text(
                "SELECT status, warehouse_id FROM pos_receipts "
                "WHERE id = :id AND tenant_id = :tid FOR UPDATE"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_uuid, "tid": tenant_id},
        ).first()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")
        if receipt[0] != "paid":
            raise HTTPException(status_code=400, detail="Recibo no está pagado")

        warehouse_uuid = receipt[1]
        if not warehouse_uuid:
            raise HTTPException(status_code=400, detail="Recibo sin warehouse_id")

        has_refunds = db.execute(
            text(
                "SELECT 1 FROM pos_receipt_lines WHERE receipt_id = :rid AND qty < 0 LIMIT 1"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).first()
        if has_refunds:
            raise HTTPException(status_code=400, detail="Recibo ya reembolsado")

        lines = db.execute(
            text(
                "SELECT product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                "net_total, cogs_unit, cogs_total, uom "
                "FROM pos_receipt_lines WHERE receipt_id = :rid"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        if not lines:
            raise HTTPException(status_code=400, detail="Recibo sin líneas")

        costing = InventoryCostingService(db)
        costing_method = resolve_inventory_costing_method(db)

        for line in lines:
            product_id = line[0]
            qty = float(line[1])
            unit_price = float(line[2])
            tax_rate = float(line[3] or 0)
            discount_pct = float(line[4] or 0)
            line_total = float(line[5] or 0)
            net_total = float(line[6] or 0)
            cogs_unit = float(line[7] or 0)
            cogs_total = float(line[8] or 0)
            uom = line[9] or "unit"

            qty_return = abs(qty)
            qty_dec = to_decimal_q(qty_return, "0.000001")
            cogs_unit_dec = to_decimal_q(cogs_unit, "0.000001")

            stock_rows = load_locked_stock_rows(db, warehouse_uuid, product_id)
            current_qty = sum_stock_rows_qty(stock_rows)
            stock_item = ensure_generic_stock_row(
                db,
                tenant_id=tenant_id,
                warehouse_id=warehouse_uuid,
                product_id=product_id,
            )
            generic_qty = float(stock_item[1] or 0)

            if costing_method == "fifo":
                costing.apply_inbound_fifo(
                    str(tenant_id),
                    str(warehouse_uuid),
                    str(product_id),
                    qty=qty_dec,
                    unit_cost=cogs_unit_dec,
                )
            elif costing_method == "lifo":
                costing.apply_inbound_lifo(
                    str(tenant_id),
                    str(warehouse_uuid),
                    str(product_id),
                    qty=qty_dec,
                    unit_cost=cogs_unit_dec,
                )
            else:
                costing.apply_inbound(
                    str(tenant_id),
                    str(warehouse_uuid),
                    str(product_id),
                    qty=qty_dec,
                    unit_cost=cogs_unit_dec,
                    initial_qty=to_decimal_q(current_qty, "0.000001"),
                    initial_avg_cost=cogs_unit_dec,
                )

            db.execute(
                text("UPDATE stock_items SET qty = :q WHERE id = :id").bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True))
                ),
                {"q": generic_qty + qty_return, "id": stock_item[0]},
            )

            refund_net = -abs(net_total or line_total)
            refund_cogs_total = -abs(cogs_total)
            refund_profit = to_decimal_q(refund_net - refund_cogs_total, "0.01")
            refund_margin = (
                to_decimal_q(refund_profit / Decimal(str(refund_net)), "0.0001")
                if refund_net != 0
                else to_decimal_q(0, "0.0001")
            )

            db.execute(
                text(
                    "INSERT INTO pos_receipt_lines("
                    "receipt_id, product_id, qty, unit_price, tax_rate, discount_pct, line_total, "
                    "uom, net_total, cogs_unit, cogs_total, gross_profit, gross_margin_pct"
                    ") VALUES ("
                    ":rid, :pid, :qty, :up, :tr, :dp, :lt, :uom, :net, :cu, :ct, :gp, :gmp"
                    ")"
                ).bindparams(
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "rid": receipt_uuid,
                    "pid": product_id,
                    "qty": -abs(qty),
                    "up": unit_price,
                    "tr": tax_rate,
                    "dp": discount_pct,
                    "lt": -abs(line_total),
                    "uom": uom,
                    "net": refund_net,
                    "cu": float(cogs_unit_dec),
                    "ct": refund_cogs_total,
                    "gp": float(refund_profit),
                    "gmp": float(refund_margin),
                },
            )

            db.execute(
                text(
                    "INSERT INTO stock_moves("
                    "tenant_id, product_id, warehouse_id, qty, kind, ref_type, ref_id, "
                    "tentative, posted, unit_cost, total_cost, occurred_at"
                    ") VALUES ("
                    ":tid, :pid, :wid, :q, 'return', 'pos_receipt_refund', :rid, "
                    "FALSE, TRUE, :uc, :tc, :occurred_at"
                    ")"
                ).bindparams(
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                    bindparam("pid", type_=PGUUID(as_uuid=True)),
                    bindparam("wid", type_=PGUUID(as_uuid=True)),
                    bindparam("rid", type_=PGUUID(as_uuid=True)),
                ),
                {
                    "tid": tenant_id,
                    "pid": product_id,
                    "wid": warehouse_uuid,
                    "q": qty_return,
                    "rid": receipt_uuid,
                    "uc": float(cogs_unit_dec),
                    "tc": float(cogs_unit_dec * qty_dec),
                    "occurred_at": datetime.utcnow(),
                },
            )

        db.commit()

        try:
            db.execute(
                text(
                    "UPDATE pos_receipts SET status = 'refunded' "
                    "WHERE id = :id AND tenant_id = :tid"
                ).bindparams(
                    bindparam("id", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"id": receipt_uuid, "tid": tenant_id},
            )
            db.commit()
        except Exception:
            db.rollback()

        documents_created: dict = {}
        try:
            from app.modules.pos.application.invoice_integration import POSInvoicingService

            service = POSInvoicingService(db, tenant_id)
            expense_result = service.create_expense_from_receipt(
                receipt_uuid,
                expense_type="refund",
                refund_reason=payload.reason,
                payment_method=("cash" if payload.refund_method == "cash" else None),
            )
            if expense_result:
                documents_created["expense"] = expense_result
        except Exception as e:
            logger.warning("Error creating refund documents: %s", e)

        try:
            claims = get_claims(request)
            user_id = claims.get("user_id")
            audit_event(
                db,
                action="refund",
                entity_type="pos_receipt",
                entity_id=str(receipt_uuid),
                actor_type="user" if user_id else "system",
                source="api",
                tenant_id=str(tenant_id),
                user_id=str(user_id) if user_id else None,
                changes={
                    "status": "refunded",
                    "reason": payload.reason,
                    "documents_created": list(documents_created.keys()),
                },
                req=request,
            )
        except Exception:
            pass

        return {
            "ok": True,
            "receipt_id": str(receipt_uuid),
            "status": "refunded",
            "documents_created": documents_created,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al reembolsar: {str(e)}")


# ============================================================================
# BACKFILL
# ============================================================================


@router.post(
    "/receipts/{receipt_id}/backfill_documents",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.receipt.read"))],
)
def backfill_receipt_documents(
    receipt_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Crea documentos faltantes para un recibo ya pagado (rescate idempotente)."""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    for_update = " FOR UPDATE" if getattr(db.get_bind().dialect, "name", "") != "sqlite" else ""
    receipt = db.execute(
        text(f"SELECT status FROM pos_receipts WHERE id = :id AND tenant_id = :tid{for_update}"),
        {"id": receipt_uuid, "tid": tenant_id},
    ).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    if receipt[0] != "paid":
        raise HTTPException(status_code=400, detail="invalid_status")

    documents_created: dict = {}
    try:
        from app.modules.pos.application.invoice_integration import POSInvoicingService

        service = POSInvoicingService(db, tenant_id)
        invoice_result = service.create_invoice_from_receipt(receipt_uuid, customer_id=None)
        if invoice_result:
            documents_created["invoice"] = invoice_result
        sale_result = service.create_sale_from_receipt(receipt_uuid)
        if sale_result:
            documents_created["sale"] = sale_result
    except Exception as e:
        logger.warning("Error backfilling documents: %s", e)

    return {"ok": True, "receipt_id": str(receipt_uuid), "documents_created": documents_created}


# ============================================================================
# PRINT
# ============================================================================


@router.get(
    "/receipts/{receipt_id}/print",
    dependencies=[Depends(require_permission("pos.receipt.print"))],
)
def print_receipt(
    receipt_id: str,
    request: Request,
    width: str = "58mm",
    db: Session = Depends(get_db),
):
    """Genera HTML para impresión térmica del ticket (auto-imprime con window.print)."""
    ensure_guc_from_request(request, db, persist=True)
    receipt_uuid = validate_uuid(receipt_id, "Receipt ID")
    tenant_id = get_tenant_id(request)

    try:
        receipt = db.execute(
            text(
                "SELECT r.id, r.number, r.gross_total, r.tax_total, r.created_at, r.status "
                "FROM pos_receipts r WHERE r.id = :id AND r.tenant_id = :tid"
            ).bindparams(
                bindparam("id", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"id": receipt_uuid, "tid": tenant_id},
        ).fetchone()

        if not receipt:
            raise HTTPException(status_code=404, detail="Recibo no encontrado")

        lines = db.execute(
            text(
                "SELECT rl.qty, rl.unit_price, rl.line_total, p.name "
                "FROM pos_receipt_lines rl "
                "LEFT JOIN products p ON rl.product_id = p.id "
                "WHERE rl.receipt_id = :rid ORDER BY rl.id"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        payments = db.execute(
            text(
                "SELECT method, amount FROM pos_payments WHERE receipt_id = :rid ORDER BY paid_at"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": receipt_uuid},
        ).fetchall()

        lines_html = "".join(
            f'<div class="line"><span>{ln[0]:.2f}x {ln[3] or "Producto"}</span><span>${ln[2]:.2f}</span></div>'
            for ln in lines
        )
        payments_html = "".join(
            f'<div class="line"><span>{p[0].upper()}</span><span>${p[1]:.2f}</span></div>'
            for p in payments
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Ticket {receipt[1]}</title>
    <style>
        @page {{ width: {width}; margin: 0; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ width: 100%; max-width: 48mm; font-family: 'Courier New', Courier, monospace;
               font-size: 9pt; margin: 5mm auto; padding: 0 2mm; }}
        .center {{ text-align: center; margin: 3px 0; }}
        .bold {{ font-weight: bold; }}
        .line {{ display: flex; justify-content: space-between; margin: 2px 0; font-size: 8pt; }}
        .line span:first-child {{ flex: 1; overflow: hidden; text-overflow: ellipsis;
                                  white-space: nowrap; padding-right: 5px; }}
        .line span:last-child {{ text-align: right; white-space: nowrap; }}
        hr {{ border: none; border-top: 1px dashed #000; margin: 5px 0; }}
        .total {{ margin-top: 5px; padding-top: 5px; font-weight: bold; font-size: 10pt; }}
        .section {{ margin: 8px 0; }}
        .section-title {{ font-weight: bold; margin-bottom: 3px; font-size: 8pt; }}
        @media print {{ body {{ margin: 0; padding: 2mm; }} }}
    </style>
</head>
<body>
    <div class="center bold" style="font-size: 11pt;">TICKET DE VENTA</div>
    <div class="center">Nº {receipt[1] or "N/A"}</div>
    <div class="center" style="font-size: 8pt;">{receipt[4].strftime("%d/%m/%Y %H:%M") if receipt[4] else ""}</div>
    <hr>
    <div class="section">
        <div class="section-title">PRODUCTOS</div>
        {lines_html}
    </div>
    <hr>
    <div class="line"><span>SUBTOTAL</span><span>${(receipt[2] - receipt[3]):.2f}</span></div>
    <div class="line"><span>IVA</span><span>${receipt[3]:.2f}</span></div>
    <div class="total line"><span>TOTAL</span><span>${receipt[2]:.2f}</span></div>
    {"<hr><div class='section'><div class='section-title'>PAGOS</div>" + payments_html + "</div>" if payments else ""}
    <hr>
    <div class="center" style="margin-top: 10px; font-size: 8pt;">¡Gracias por su compra!</div>
    <script>window.addEventListener('load', function() {{ setTimeout(function() {{ window.print(); }}, 500); }});</script>
</body>
</html>"""

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar impresión: {str(e)}")
