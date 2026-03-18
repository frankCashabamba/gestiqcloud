"""POS — Router de turnos (shifts)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls
from app.models.accounting.chart_of_accounts import JournalEntry as AsientoContable
from app.models.accounting.chart_of_accounts import JournalEntryLine as AsientoLinea
from app.models.accounting.pos_settings import PaymentMethod, TenantAccountingSettings
from app.modules.accounting.interface.http.tenant import _generate_numero_asiento

from ._deps import (
    CloseShiftIn,
    OpenShiftIn,
    ensure_pos_accounting_settings,
    get_tenant_id,
    get_user_id,
    validate_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Shifts"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


@router.post(
    "/shifts",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.open"))],
)
def open_shift(payload: OpenShiftIn, request: Request, db: Session = Depends(get_db)):
    """Abre un nuevo turno en un registro POS."""
    ensure_guc_from_request(request, db, persist=True)
    user_id = get_user_id(request)
    tenant_id = get_tenant_id(request)
    register_uuid = validate_uuid(payload.register_id, "Register ID")

    try:
        register = db.execute(
            text(
                "SELECT active FROM pos_registers WHERE id = :rid AND tenant_id = :tid"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"rid": register_uuid, "tid": tenant_id},
        ).first()

        if not register:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        if not register[0]:
            raise HTTPException(status_code=400, detail="El registro está inactivo")

        existing = db.execute(
            text(
                "SELECT id FROM pos_shifts WHERE register_id = :rid AND status = 'open' FOR UPDATE"
            ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
            {"rid": register_uuid},
        ).first()

        if existing:
            raise HTTPException(
                status_code=400, detail="Ya existe un turno abierto para este registro"
            )

        opened_at = datetime.now(UTC)
        row = db.execute(
            text(
                "INSERT INTO pos_shifts(register_id, opened_by, opened_at, opening_float, status) "
                "VALUES (:rid, :opened_by, :opened_at, :opening_float, 'open') "
                "RETURNING id"
            ).bindparams(
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("opened_by", type_=PGUUID(as_uuid=True)),
                bindparam("opened_at"),
            ),
            {
                "rid": register_uuid,
                "opened_by": user_id,
                "opened_at": opened_at,
                "opening_float": payload.opening_float,
            },
        ).first()

        db.commit()
        return {"id": str(row[0]), "status": "open"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al abrir turno: {str(e)}")


@router.get(
    "/shifts/current/{register_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.read"))],
)
def get_current_shift(register_id: str, request: Request, db: Session = Depends(get_db)):
    """Obtiene el turno abierto (si existe) para un registro."""
    ensure_guc_from_request(request, db, persist=True)
    rid = validate_uuid(register_id, "Register ID")

    shift = db.execute(
        text(
            "SELECT id, register_id, opened_by, opened_at, closed_at, opening_float, "
            "closing_total, status "
            "FROM pos_shifts "
            "WHERE register_id = :rid AND status = 'open' "
            "ORDER BY opened_at DESC LIMIT 1"
        ).bindparams(bindparam("rid", type_=PGUUID(as_uuid=True))),
        {"rid": rid},
    ).first()

    if not shift:
        raise HTTPException(status_code=404, detail="No hay turno abierto para este registro")

    return {
        "id": str(shift[0]),
        "register_id": str(shift[1]),
        "opened_by": str(shift[2]),
        "opened_at": shift[3].isoformat() if shift[3] else None,
        "closed_at": shift[4].isoformat() if shift[4] else None,
        "opening_float": float(shift[5] or 0),
        "closing_total": float(shift[6] or 0) if shift[6] is not None else None,
        "status": shift[7],
    }


@router.get(
    "/shifts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.shift.read"))],
)
def list_shifts(
    request: Request,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    """Lista turnos POS con filtros opcionales."""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT id, register_id, opened_at, closed_at, opening_float, closing_cash, status, opened_by "
        "FROM pos_shifts WHERE 1=1"
    ]
    params: dict = {}

    if status:
        sql_parts.append("AND status = :st")
        params["st"] = status
    if since:
        sql_parts.append("AND opened_at >= :since")
        params["since"] = since
    if until:
        sql_parts.append("AND opened_at <= :until")
        params["until"] = until

    sql_parts.append(f"ORDER BY opened_at DESC LIMIT {min(limit, 1000)}")

    try:
        rows = db.execute(text(" ".join(sql_parts)), params).fetchall()
        return [
            {
                "id": str(r[0]),
                "register_id": str(r[1]),
                "opened_at": r[2].isoformat() if r[2] else None,
                "closed_at": r[3].isoformat() if r[3] else None,
                "opening_float": float(r[4]) if r[4] else 0,
                "closing_cash": float(r[5]) if r[5] else None,
                "status": r[6],
                "opened_by": str(r[7]),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar turnos: {str(e)}")


@router.get(
    "/shifts/{shift_id}/summary",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def get_shift_summary(
    shift_id: str,
    request: Request,
    cashier_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Resumen del turno: ventas, productos vendidos y stock restante."""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = validate_uuid(shift_id, "Shift ID")
    tenant_id = get_tenant_id(request)
    cashier_uuid = validate_uuid(cashier_id, "Cashier ID") if cashier_id else None

    base_filter = "shift_id = :sid"
    params: dict = {"sid": shift_uuid, "tid": tenant_id}
    if cashier_uuid:
        base_filter += " AND cashier_id = :cid"
        params["cid"] = cashier_uuid

    try:
        pending_receipts = db.execute(
            text(
                f"SELECT COUNT(*) FROM pos_receipts "
                f"WHERE {base_filter} AND tenant_id = :tid AND status IN ('draft', 'unpaid')"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            params,
        ).scalar()

        items_sold = db.execute(
            text(
                "SELECT rl.product_id, p.name, p.sku AS code, "
                "SUM(rl.qty) as qty_sold, "
                "SUM(rl.qty * rl.unit_price * (1 - rl.discount_pct/100)) as subtotal "
                "FROM pos_receipt_lines rl "
                "JOIN pos_receipts r ON r.id = rl.receipt_id "
                "LEFT JOIN products p ON p.id = rl.product_id "
                f"WHERE r.{base_filter} AND r.tenant_id = :tid AND r.status = 'paid' "
                "GROUP BY rl.product_id, p.id, p.name, p.sku "
                "ORDER BY p.name"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            params,
        ).fetchall()

        product_ids = [row[0] for row in items_sold if row[0]]
        stock_items: dict = {}
        if product_ids:
            stock_rows = db.execute(
                text(
                    "SELECT si.product_id, si.warehouse_id, w.name as warehouse_name, si.qty "
                    "FROM stock_items si "
                    "LEFT JOIN warehouses w ON w.id = si.warehouse_id "
                    "WHERE si.product_id = ANY(:product_ids)"
                ),
                {"product_ids": product_ids},
            ).fetchall()
            for row in stock_rows:
                pid = str(row[0])
                stock_items.setdefault(pid, []).append(
                    {
                        "warehouse_id": str(row[1]),
                        "warehouse_name": row[2],
                        "qty": float(row[3] or 0),
                    }
                )

        items = [
            {
                "product_id": str(row[0]) if row[0] else None,
                "name": row[1],
                "code": row[2],
                "qty_sold": float(row[3] or 0),
                "subtotal": float(row[4] or 0),
                "stock": stock_items.get(str(row[0]), []) if row[0] else [],
            }
            for row in items_sold
        ]

        sales_total = db.execute(
            text(
                f"SELECT COALESCE(SUM(gross_total), 0) "
                f"FROM pos_receipts WHERE {base_filter} AND tenant_id = :tid AND status = 'paid'"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            params,
        ).scalar()

        payments_breakdown_rows = db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) as total "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                f"WHERE pr.{base_filter} AND pr.tenant_id = :tid AND pr.status = 'paid' "
                "GROUP BY pp.method"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            params,
        ).fetchall()
        payments_breakdown = {row[0]: float(row[1] or 0) for row in payments_breakdown_rows}

        return {
            "pending_receipts": pending_receipts or 0,
            "items_sold": items,
            "sales_total": float(sales_total or 0),
            "receipts_count": len(items_sold),
            "payments": payments_breakdown,
        }

    except Exception as e:
        logger.error("Error getting shift summary: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


@router.get(
    "/shifts/{shift_id}/summary-basic",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def get_shift_summary_basic(shift_id: str, request: Request, db: Session = Depends(get_db)):
    """Resumen básico de un turno: pagos y conteo de recibos."""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = validate_uuid(shift_id, "Shift ID")
    tenant_id = get_tenant_id(request)

    try:
        payments = db.execute(
            text(
                "SELECT pp.method, COALESCE(SUM(pp.amount), 0) AS amount "
                "FROM pos_payments pp "
                "JOIN pos_receipts pr ON pr.id = pp.receipt_id "
                "WHERE pr.shift_id = :sid AND pr.tenant_id = :tid "
                "GROUP BY pp.method ORDER BY amount DESC"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).fetchall()

        receipts = db.execute(
            text(
                "SELECT "
                "COUNT(*) FILTER (WHERE status = 'paid') AS paid, "
                "COUNT(*) FILTER (WHERE status = 'draft') AS draft "
                "FROM pos_receipts WHERE shift_id = :sid AND tenant_id = :tid"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).first()

        totals = db.execute(
            text(
                "SELECT COALESCE(SUM(gross_total), 0) AS gross, COALESCE(SUM(tax_total), 0) AS tax "
                "FROM pos_receipts "
                "WHERE shift_id = :sid AND tenant_id = :tid AND status = 'paid'"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).first()

        return {
            "shift_id": shift_id,
            "receipts": {"paid": int(receipts[0] or 0), "draft": int(receipts[1] or 0)},
            "payments": [{"method": p[0], "amount": float(p[1])} for p in payments],
            "totals": {
                "gross": float(totals[0] or 0),
                "tax": float(totals[1] or 0),
                "total": float((totals[0] or 0) + (totals[1] or 0)),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")


@router.post(
    "/shifts/{shift_id}/close",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.shift.close"))],
)
def close_shift(
    shift_id: str,
    payload: CloseShiftIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cierra un turno POS generando el asiento contable y el reporte diario."""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = validate_uuid(shift_id, "Shift ID")
    token_tenant_id = get_tenant_id(request)

    try:
        shift = db.execute(
            text("SELECT status FROM pos_shifts WHERE id = :sid FOR UPDATE").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).first()

        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")
        if shift[0] != "open":
            raise HTTPException(status_code=400, detail="El turno ya está cerrado")

        pending = db.execute(
            text(
                "SELECT COUNT(*) FROM pos_receipts "
                "WHERE shift_id = :sid AND tenant_id = :tid AND status IN ('draft', 'unpaid')"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": token_tenant_id},
        ).scalar()

        if pending and pending > 0:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede cerrar el turno. Hay {pending} recibo(s) sin cobrar.",
            )

        shift_data = db.execute(
            text(
                "SELECT ps.register_id, ps.opened_at, ps.opening_float, pr.tenant_id "
                "FROM pos_shifts ps "
                "JOIN pos_registers pr ON pr.id = ps.register_id "
                "WHERE ps.id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()

        if not shift_data:
            raise HTTPException(status_code=404, detail="Datos del turno no encontrados")

        register_id = shift_data[0]
        opened_at = shift_data[1]
        opening_float = float(shift_data[2] or 0)
        tenant_id = shift_data[3]

        if str(tenant_id) != str(token_tenant_id):
            logger.warning(
                "Tenant mismatch closing shift: shift_tenant=%s token_tenant=%s shift=%s",
                tenant_id,
                token_tenant_id,
                shift_uuid,
            )
            raise HTTPException(status_code=403, detail="tenant_mismatch")

        sales_by_method = db.execute(
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
            {"sid": shift_uuid, "tid": tenant_id},
        ).fetchall()

        cash_sales = 0.0
        card_sales = 0.0
        other_sales = 0.0
        total_sales = 0.0

        for method, amount in sales_by_method:
            total_sales += float(amount)
            mkey = (method or "").strip().lower()
            if mkey == "cash":
                cash_sales = float(amount)
            elif mkey in ("card", "credit", "debit"):
                card_sales = float(amount)
            else:
                other_sales += float(amount)

        expected_cash = opening_float + cash_sales

        tax_total = float(
            db.execute(
                text(
                    "SELECT COALESCE(SUM(tax_total), 0) FROM pos_receipts "
                    "WHERE shift_id = :sid AND tenant_id = :tid AND status = 'paid'"
                ).bindparams(
                    bindparam("sid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"sid": shift_uuid, "tid": tenant_id},
            ).scalar()
            or 0
        )
        net_total = total_sales - tax_total

        # --- Close the shift (always succeeds) ---
        db.execute(
            text(
                "UPDATE pos_shifts "
                "SET status = 'closed', closed_at = NOW(), closing_total = :ct "
                "WHERE id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid, "ct": payload.closing_cash},
        )

        count_date = opened_at.date() if opened_at else datetime.now(UTC).date()
        db.execute(
            text(
                "INSERT INTO pos_daily_counts "
                "(tenant_id, register_id, shift_id, count_date, opening_float, "
                "cash_sales, card_sales, other_sales, total_sales, expected_cash, "
                "counted_cash, discrepancy, loss_amount, loss_note) "
                "VALUES (:tid, :rid, :sid, :cd, :of, :cs, :cars, :os, :ts, :ec, :cc, :disc, :la, :ln)"
            ).bindparams(
                bindparam("tid", type_=PGUUID(as_uuid=True)),
                bindparam("rid", type_=PGUUID(as_uuid=True)),
                bindparam("sid", type_=PGUUID(as_uuid=True)),
            ),
            {
                "tid": tenant_id,
                "rid": register_id,
                "sid": shift_uuid,
                "cd": count_date,
                "of": opening_float,
                "cs": cash_sales,
                "cars": card_sales,
                "os": other_sales,
                "ts": total_sales,
                "ec": expected_cash,
                "cc": payload.closing_cash,
                "disc": payload.closing_cash - expected_cash,
                "la": payload.loss_amount or 0,
                "ln": payload.loss_note,
            },
        )

        db.commit()

        # --- Automatic accounting (best-effort) ---
        accounting_result = None
        try:
            ensure_guc_from_request(request, db, persist=True)
            settings = db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()
            if settings:
                ensure_pos_accounting_settings(settings)
                pm_rows = (
                    db.query(PaymentMethod).filter_by(tenant_id=tenant_id, is_active=True).all()
                )
                pm_map = {p.name.strip().lower(): p.account_id for p in pm_rows}

                existing_entry = db.execute(
                    text(
                        "SELECT id FROM journal_entries "
                        "WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = :sid AND tenant_id = :tid"
                    ).bindparams(
                        bindparam("sid", type_=PGUUID(as_uuid=True)),
                        bindparam("tid", type_=PGUUID(as_uuid=True)),
                    ),
                    {"sid": shift_uuid, "tid": tenant_id},
                ).first()

                if not existing_entry:
                    acc_lines: list[AsientoLinea] = []
                    debit_total = 0.0
                    credit_total = 0.0

                    for method, amount in sales_by_method:
                        amt = float(amount or 0)
                        if amt <= 0:
                            continue
                        mkey = (method or "").strip().lower()
                        account_id = pm_map.get(mkey)
                        if not account_id:
                            if mkey in ("cash", "efectivo"):
                                account_id = settings.cash_account_id
                            elif mkey in ("card", "tarjeta", "debit", "credit", "link"):
                                account_id = settings.bank_account_id
                            else:
                                account_id = settings.cash_account_id
                        if account_id:
                            acc_lines.append(
                                AsientoLinea(
                                    account_id=account_id, debit=Decimal(str(round(amt, 2)))
                                )
                            )
                            debit_total += amt

                    if net_total > 0 and settings.sales_bakery_account_id:
                        acc_lines.append(
                            AsientoLinea(
                                account_id=settings.sales_bakery_account_id,
                                debit=Decimal("0"),
                                credit=Decimal(str(round(net_total, 2))),
                            )
                        )
                        credit_total += net_total

                    if tax_total > 0 and settings.vat_output_account_id:
                        acc_lines.append(
                            AsientoLinea(
                                account_id=settings.vat_output_account_id,
                                debit=Decimal("0"),
                                credit=Decimal(str(round(tax_total, 2))),
                            )
                        )
                        credit_total += tax_total

                    if payload.loss_amount and payload.loss_amount > 0 and settings.loss_account_id:
                        acc_lines.append(
                            AsientoLinea(
                                account_id=settings.loss_account_id,
                                debit=Decimal(str(round(payload.loss_amount, 2))),
                                credit=Decimal("0"),
                            )
                        )
                        acc_lines.append(
                            AsientoLinea(
                                account_id=settings.cash_account_id,
                                debit=Decimal("0"),
                                credit=Decimal(str(round(payload.loss_amount, 2))),
                            )
                        )
                        debit_total += float(payload.loss_amount)
                        credit_total += float(payload.loss_amount)

                    if acc_lines and round(debit_total - credit_total, 2) == 0:
                        number = _generate_numero_asiento(db, tenant_id, datetime.now(UTC).year)
                        entry = AsientoContable(
                            tenant_id=tenant_id,
                            number=number,
                            date=datetime.now(UTC).date(),
                            type="OPERATIONS",
                            description=f"Cierre turno POS {shift_id}",
                            ref_doc_type="POS_SHIFT",
                            ref_doc_id=shift_uuid,
                            debit_total=Decimal(str(round(debit_total, 2))),
                            credit_total=Decimal(str(round(credit_total, 2))),
                            is_balanced=True,
                            status="POSTED",
                        )
                        db.add(entry)
                        db.flush()
                        for idx, line in enumerate(acc_lines):
                            line.entry_id = entry.id
                            line.line_number = idx + 1
                            db.add(line)
                        db.commit()
                        accounting_result = {"entry_id": str(entry.id), "status": "posted"}
        except Exception as e:
            logger.warning("Accounting auto-generation failed for shift %s: %s", shift_id, e)
            try:
                db.rollback()
            except Exception:
                pass

        result = {
            "status": "closed",
            "expected_cash": expected_cash,
            "counted_cash": payload.closing_cash,
            "difference": payload.closing_cash - expected_cash,
            "total_sales": total_sales,
            "cash_sales": cash_sales,
            "card_sales": card_sales,
            "loss_amount": payload.loss_amount or 0,
            "loss_note": payload.loss_note,
        }
        if accounting_result:
            result["accounting"] = accounting_result
        return result

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al cerrar turno: {str(e)}")


@router.post(
    "/shifts/{shift_id}/accounting",
    response_model=dict,
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def generate_accounting_for_closed_shift(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """Genera asiento contable para un turno ya cerrado (idempotente si no existe)."""
    ensure_guc_from_request(request, db, persist=True)
    shift_uuid = validate_uuid(shift_id, "Shift ID")
    token_tenant_id = get_tenant_id(request)

    try:
        shift = db.execute(
            text("SELECT status, register_id FROM pos_shifts WHERE id = :sid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).first()
        if not shift:
            raise HTTPException(status_code=404, detail="Turno no encontrado")
        if shift[0] != "closed":
            raise HTTPException(status_code=400, detail="El turno debe estar cerrado")

        shift_data = db.execute(
            text(
                "SELECT ps.opening_float, pr.tenant_id FROM pos_shifts ps "
                "JOIN pos_registers pr ON pr.id = ps.register_id "
                "WHERE ps.id = :sid"
            ).bindparams(bindparam("sid", type_=PGUUID(as_uuid=True))),
            {"sid": shift_uuid},
        ).first()
        if not shift_data:
            raise HTTPException(status_code=404, detail="Datos del turno no encontrados")

        tenant_id = shift_data[1]
        if str(tenant_id) != str(token_tenant_id):
            raise HTTPException(status_code=403, detail="tenant_mismatch")

        existing_entry = db.execute(
            text(
                "SELECT id FROM journal_entries "
                "WHERE ref_doc_type = 'POS_SHIFT' AND ref_doc_id = :sid AND tenant_id = :tid"
            ).bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True)),
                bindparam("tid", type_=PGUUID(as_uuid=True)),
            ),
            {"sid": shift_uuid, "tid": tenant_id},
        ).first()
        if existing_entry:
            raise HTTPException(
                status_code=400, detail="Ya existe un asiento contable para este turno"
            )

        sales_by_method = db.execute(
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
            {"sid": shift_uuid, "tid": tenant_id},
        ).fetchall()

        total_sales = sum(float(amount or 0) for _, amount in sales_by_method)

        tax_total = float(
            db.execute(
                text(
                    "SELECT COALESCE(SUM(tax_total), 0) FROM pos_receipts "
                    "WHERE shift_id = :sid AND tenant_id = :tid AND status = 'paid'"
                ).bindparams(
                    bindparam("sid", type_=PGUUID(as_uuid=True)),
                    bindparam("tid", type_=PGUUID(as_uuid=True)),
                ),
                {"sid": shift_uuid, "tid": tenant_id},
            ).scalar()
            or 0.0
        )
        net_total = total_sales - tax_total

        settings = db.query(TenantAccountingSettings).filter_by(tenant_id=tenant_id).first()
        if not settings:
            raise HTTPException(
                status_code=400, detail="Config contable POS no configurada para este tenant"
            )
        ensure_pos_accounting_settings(settings)

        pm_rows = db.query(PaymentMethod).filter_by(tenant_id=tenant_id, is_active=True).all()
        pm_map = {p.name.strip().lower(): p.account_id for p in pm_rows}

        lines: list[AsientoLinea] = []
        debit_total = 0.0
        credit_total = 0.0

        for method, amount in sales_by_method:
            amt = float(amount or 0)
            if amt <= 0:
                continue
            mkey = (method or "").strip().lower()
            account_id = pm_map.get(mkey)
            if not account_id:
                if mkey in ("cash", "efectivo"):
                    account_id = settings.cash_account_id
                elif mkey in ("card", "tarjeta", "debit", "credit", "link"):
                    account_id = settings.bank_account_id
                else:
                    account_id = settings.cash_account_id
            if not account_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay cuenta contable para el medio de pago: {method}",
                )
            lines.append(AsientoLinea(account_id=account_id, debit=Decimal(str(round(amt, 2)))))
            debit_total += amt

        if net_total > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.sales_bakery_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(net_total, 2))),
                )
            )
            credit_total += net_total

        if tax_total > 0:
            lines.append(
                AsientoLinea(
                    account_id=settings.vat_output_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(tax_total, 2))),
                )
            )
            credit_total += tax_total

        loss_amount = db.execute(
            text("SELECT loss_amount FROM pos_daily_counts WHERE shift_id = :sid").bindparams(
                bindparam("sid", type_=PGUUID(as_uuid=True))
            ),
            {"sid": shift_uuid},
        ).scalar()
        if loss_amount and loss_amount > 0:
            if not settings.loss_account_id:
                raise HTTPException(
                    status_code=400, detail="Config contable: falta cuenta de pérdidas/mermas"
                )
            lines.append(
                AsientoLinea(
                    account_id=settings.loss_account_id,
                    debit=Decimal(str(round(loss_amount, 2))),
                    credit=Decimal("0"),
                )
            )
            lines.append(
                AsientoLinea(
                    account_id=settings.cash_account_id,
                    debit=Decimal("0"),
                    credit=Decimal(str(round(loss_amount, 2))),
                )
            )
            debit_total += float(loss_amount)
            credit_total += float(loss_amount)

        if round(debit_total - credit_total, 2) != 0:
            raise HTTPException(status_code=400, detail="Asiento no balanceado")

        number = _generate_numero_asiento(db, tenant_id, datetime.now(UTC).year)
        entry = AsientoContable(
            tenant_id=tenant_id,
            number=number,
            date=datetime.now(UTC).date(),
            type="OPERATIONS",
            description=f"Contabilización turno POS {shift_id}",
            ref_doc_type="POS_SHIFT",
            ref_doc_id=shift_uuid,
            debit_total=Decimal(str(round(debit_total, 2))),
            credit_total=Decimal(str(round(credit_total, 2))),
            is_balanced=True,
            status="POSTED",
        )
        db.add(entry)
        db.flush()
        for idx, line in enumerate(lines):
            line.entry_id = entry.id
            line.line_number = idx + 1
            db.add(line)
        db.commit()

        return {
            "status": "accounted",
            "entry_id": str(entry.id),
            "total_sales": total_sales,
            "debit": debit_total,
            "credit": credit_total,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error("Error generating accounting for shift: %s", str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al contabilizar turno: {str(e)}")
