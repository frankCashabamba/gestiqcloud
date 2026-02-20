"""Profit Reports API — Snapshot-based fast queries"""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.profit_snapshots import ProductProfitSnapshot, ProfitSnapshotDaily
from app.modules.reports.application.recalculation_service import RecalculationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports-profit"])


@router.get("/profit")
def get_profit_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    """Get profit report from snapshots."""
    tenant_id = db.info.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    snapshots = (
        db.query(ProfitSnapshotDaily)
        .filter(
            ProfitSnapshotDaily.tenant_id == tenant_id,
            ProfitSnapshotDaily.date >= date_from,
            ProfitSnapshotDaily.date <= date_to,
        )
        .order_by(ProfitSnapshotDaily.date.asc())
        .all()
    )

    # Aggregated totals
    total_sales = sum(float(s.total_sales or 0) for s in snapshots)
    total_cogs = sum(float(s.total_cogs or 0) for s in snapshots)
    gross_profit = sum(float(s.gross_profit or 0) for s in snapshots)
    total_expenses = sum(float(s.total_expenses or 0) for s in snapshots)
    net_profit = sum(float(s.net_profit or 0) for s in snapshots)
    total_orders = sum(s.order_count or 0 for s in snapshots)

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "summary": {
            "total_sales": total_sales,
            "total_cogs": total_cogs,
            "gross_profit": gross_profit,
            "gross_margin_pct": round(gross_profit / total_sales * 100, 2)
            if total_sales > 0
            else 0,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
            "net_margin_pct": round(net_profit / total_sales * 100, 2) if total_sales > 0 else 0,
            "total_orders": total_orders,
        },
        "daily": [
            {
                "date": s.date.isoformat(),
                "sales": float(s.total_sales or 0),
                "cogs": float(s.total_cogs or 0),
                "gross_profit": float(s.gross_profit or 0),
                "expenses": float(s.total_expenses or 0),
                "net_profit": float(s.net_profit or 0),
                "orders": s.order_count or 0,
            }
            for s in snapshots
        ],
    }


@router.get("/product-margins")
def get_product_margins(
    date_from: date = Query(...),
    date_to: date = Query(...),
    limit: int = Query(50, le=200),
    sort_by: str = Query("revenue", regex="^(revenue|margin_pct|cogs|sold_qty)$"),
    db: Session = Depends(get_db),
):
    """Get product profit margins from snapshots."""
    tenant_id = db.info.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    results = (
        db.query(
            ProductProfitSnapshot.product_id,
            func.sum(ProductProfitSnapshot.revenue).label("revenue"),
            func.sum(ProductProfitSnapshot.cogs).label("cogs"),
            func.sum(ProductProfitSnapshot.gross_profit).label("gross_profit"),
            func.sum(ProductProfitSnapshot.sold_qty).label("sold_qty"),
            func.sum(ProductProfitSnapshot.waste_qty).label("waste_qty"),
        )
        .filter(
            ProductProfitSnapshot.tenant_id == tenant_id,
            ProductProfitSnapshot.date >= date_from,
            ProductProfitSnapshot.date <= date_to,
        )
        .group_by(ProductProfitSnapshot.product_id)
        .all()
    )

    products_data = []
    for r in results:
        revenue = float(r[1] or 0)
        cogs = float(r[2] or 0)
        gross = float(r[3] or 0)
        margin = round(gross / revenue * 100, 2) if revenue > 0 else 0
        products_data.append(
            {
                "product_id": str(r[0]),
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross,
                "margin_pct": margin,
                "sold_qty": float(r[4] or 0),
                "waste_qty": float(r[5] or 0),
            }
        )

    # Sort
    reverse = True
    products_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "products": products_data[:limit],
    }


@router.post("/recalculate")
def trigger_recalculation(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    """Manually trigger profit snapshot recalculation."""
    tenant_id = db.info.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context required")

    tid = UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    svc = RecalculationService(db)
    snapshots = svc.recalculate_range(tid, date_from, date_to)
    db.commit()

    return {
        "status": "completed",
        "days_recalculated": len(snapshots),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
    }
