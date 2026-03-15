"""POS — Router de reportes diarios de caja (daily counts)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

from ._deps import validate_uuid

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Daily Counts"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


@router.get(
    "/daily_counts",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.reports.view"))],
)
def list_daily_counts(
    request: Request,
    register_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    """Lista los reportes diarios de caja."""
    ensure_guc_from_request(request, db, persist=True)

    sql_parts = [
        "SELECT pdc.id, pdc.register_id, pdc.shift_id, pdc.count_date, pdc.opening_float, "
        "pdc.cash_sales, pdc.card_sales, pdc.other_sales, pdc.total_sales, pdc.expected_cash, "
        "pdc.counted_cash, pdc.discrepancy, pdc.loss_amount, pdc.loss_note, pdc.created_at, "
        "CASE WHEN je.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_journal_entry "
        "FROM pos_daily_counts pdc "
        "LEFT JOIN journal_entries je "
        "  ON je.ref_doc_type = 'POS_SHIFT' AND je.ref_doc_id = pdc.shift_id "
        "WHERE 1=1"
    ]
    params: dict = {}

    if register_id:
        rid = validate_uuid(register_id, "Register ID")
        sql_parts.append("AND pdc.register_id = :rid")
        params["rid"] = rid

    if since:
        sql_parts.append("AND pdc.count_date >= :since")
        params["since"] = since

    if until:
        sql_parts.append("AND pdc.count_date <= :until")
        params["until"] = until

    sql_parts.append("ORDER BY pdc.count_date DESC, pdc.created_at DESC LIMIT :limit")
    params["limit"] = limit

    try:
        rows = db.execute(text(" ".join(sql_parts)), params).fetchall()

        return [
            {
                "id": str(r[0]),
                "register_id": str(r[1]),
                "shift_id": str(r[2]),
                "count_date": r[3].isoformat() if r[3] else None,
                "opening_float": float(r[4] or 0),
                "cash_sales": float(r[5] or 0),
                "card_sales": float(r[6] or 0),
                "other_sales": float(r[7] or 0),
                "total_sales": float(r[8] or 0),
                "expected_cash": float(r[9] or 0),
                "counted_cash": float(r[10] or 0),
                "discrepancy": float(r[11] or 0),
                "loss_amount": float(r[12] or 0),
                "loss_note": r[13],
                "created_at": r[14].isoformat() if r[14] else None,
                "has_journal_entry": bool(r[15]),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar reportes diarios: {str(e)}")
