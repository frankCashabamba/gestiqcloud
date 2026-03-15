"""POS — Router de analíticas de márgenes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_permission, require_scope
from app.db.rls import ensure_guc_from_request, ensure_rls

from ._deps import get_tenant_id, validate_uuid

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pos",
    tags=["POS — Analytics"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(require_permission("pos.view")),
        Depends(ensure_rls),
    ],
)


@router.get(
    "/analytics/margins/products",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_by_product(
    request: Request,
    db: Session = Depends(get_db),
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=100, le=500),
):
    from sqlalchemy import text

    ensure_guc_from_request(request, db, persist=True)
    tenant_id = get_tenant_id(request)

    rows = db.execute(
        text(
            "SELECT "
            "l.product_id, "
            "SUM(l.net_total) AS sales_net, "
            "SUM(l.cogs_total) AS cogs, "
            "SUM(l.gross_profit) AS gross_profit, "
            "CASE WHEN SUM(l.net_total) > 0 "
            "THEN SUM(l.gross_profit)/SUM(l.net_total) "
            "ELSE 0 END AS margin_pct "
            "FROM pos_receipt_lines l "
            "JOIN pos_receipts r ON r.id = l.receipt_id "
            "WHERE r.tenant_id = :tid "
            "AND r.status IN ('paid','invoiced') "
            "AND r.created_at >= :from_date "
            "AND r.created_at < :to_date "
            "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
            "GROUP BY l.product_id "
            "ORDER BY gross_profit DESC "
            "LIMIT :limit"
        ),
        {
            "tid": tenant_id,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "product_id": str(r[0]),
            "sales_net": float(r[1] or 0),
            "cogs": float(r[2] or 0),
            "gross_profit": float(r[3] or 0),
            "margin_pct": float(r[4] or 0),
        }
        for r in rows
    ]


@router.get(
    "/analytics/margins/customers",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_by_customer(
    request: Request,
    db: Session = Depends(get_db),
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=100, le=500),
):
    from sqlalchemy import text

    ensure_guc_from_request(request, db, persist=True)
    tenant_id = get_tenant_id(request)

    rows = db.execute(
        text(
            "SELECT "
            "r.customer_id, "
            "SUM(l.net_total) AS sales_net, "
            "SUM(l.cogs_total) AS cogs, "
            "SUM(l.gross_profit) AS gross_profit, "
            "CASE WHEN SUM(l.net_total) > 0 "
            "THEN SUM(l.gross_profit)/SUM(l.net_total) "
            "ELSE 0 END AS margin_pct "
            "FROM pos_receipt_lines l "
            "JOIN pos_receipts r ON r.id = l.receipt_id "
            "WHERE r.tenant_id = :tid "
            "AND r.status IN ('paid','invoiced') "
            "AND r.created_at >= :from_date "
            "AND r.created_at < :to_date "
            "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
            "GROUP BY r.customer_id "
            "ORDER BY gross_profit DESC "
            "LIMIT :limit"
        ),
        {
            "tid": tenant_id,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "customer_id": str(r[0]) if r[0] else None,
            "sales_net": float(r[1] or 0),
            "cogs": float(r[2] or 0),
            "gross_profit": float(r[3] or 0),
            "margin_pct": float(r[4] or 0),
        }
        for r in rows
    ]


@router.get(
    "/analytics/margins/product/{product_id}/lines",
    response_model=list[dict],
    dependencies=[Depends(require_permission("pos.analytics.view"))],
)
def margins_product_lines(
    product_id: str,
    request: Request,
    db: Session = Depends(get_db),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    warehouse_id: str | None = None,
    limit: int = Query(default=200, le=1000),
):
    from sqlalchemy import text

    ensure_guc_from_request(request, db, persist=True)
    tenant_id = get_tenant_id(request)
    pid = validate_uuid(product_id, "Product ID")

    sql = (
        "SELECT l.id, l.receipt_id, l.qty, l.unit_price, l.net_total, "
        "l.cogs_unit, l.cogs_total, l.gross_profit, l.gross_margin_pct, "
        "r.created_at "
        "FROM pos_receipt_lines l "
        "JOIN pos_receipts r ON r.id = l.receipt_id "
        "WHERE r.tenant_id = :tid "
        "AND r.status IN ('paid','invoiced') "
        "AND l.product_id = :pid "
        "AND (:warehouse_id IS NULL OR r.warehouse_id = :warehouse_id) "
    )
    if from_date:
        sql += "AND r.created_at >= :from_date "
    if to_date:
        sql += "AND r.created_at < :to_date "
    sql += "ORDER BY r.created_at DESC LIMIT :limit"

    rows = db.execute(
        text(sql),
        {
            "tid": tenant_id,
            "pid": pid,
            "from_date": from_date,
            "to_date": to_date,
            "warehouse_id": warehouse_id,
            "limit": limit,
        },
    ).fetchall()

    return [
        {
            "line_id": str(r[0]),
            "receipt_id": str(r[1]),
            "qty": float(r[2] or 0),
            "unit_price": float(r[3] or 0),
            "net_total": float(r[4] or 0),
            "cogs_unit": float(r[5] or 0),
            "cogs_total": float(r[6] or 0),
            "gross_profit": float(r[7] or 0),
            "gross_margin_pct": float(r[8] or 0),
            "created_at": r[9].isoformat() if r[9] else None,
        }
        for r in rows
    ]
