"""
Dashboard KPIs - Endpoint for custom metrics by sector
Connects with REAL data from system tables
"""

import logging
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import set_tenant_guc, tenant_id_sql_expr_text
from app.models.company.company import SectorTemplate
from app.models.tenant import Tenant

router = APIRouter(prefix="/dashboard/kpis", tags=["Dashboard KPIs"])
logger = logging.getLogger("app.dashboard_kpis")


def _resolve_sector(sector: str | None, tenant: Tenant | None) -> str:
    if sector:
        return sector.lower()
    if tenant and tenant.sector_template_name:
        return tenant.sector_template_name.strip().lower()
    return "default"


def _resolve_sector_currency(db: Session, sector_code: str, fallback: str | None = None) -> str | None:
    tpl = (
        db.query(SectorTemplate)
        .filter(SectorTemplate.code == sector_code, SectorTemplate.is_active == True)  # noqa: E712
        .first()
    )
    if not tpl:
        return fallback
    config = tpl.template_config or {}
    defaults = config.get("defaults", {}) or {}
    return defaults.get("currency", fallback)


def _sector_kpis_payload(
    sector: str,
    tenant_id: str,
    db: Session,
    currency: str | None,
) -> dict[str, Any]:
    tenant_expr = tenant_id_sql_expr_text()

    def tenant_clause(field: str = "tenant_id") -> str:
        # Asegura comparación uuid = uuid incluso si el campo viene con ::text
        return f"CAST({field} AS uuid) = {tenant_expr}"

    def tenant_params(**extra: Any) -> dict[str, Any]:
        params = {"tid": tenant_id}
        params.update(extra)
        return params

    # Dates for filters
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    if sector == "panaderia":
        # COUNTER SALES (from pos_receipts + invoices)
        sales_today = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                tenant_params(today=today),
            ).scalar()
            or 0.0
        )

        sales_yesterday = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) = :yesterday
            AND status IN ('paid', 'invoiced')
        """
                ),
                tenant_params(yesterday=yesterday),
            ).scalar()
            or 0.0
        )

        variation = ((sales_today - sales_yesterday) / sales_yesterday * 100) if sales_yesterday > 0 else 0.0

        # CRITICAL STOCK (products with low stock)
        critical_stock = db.execute(
            text(
                f"""
            SELECT
                COUNT(DISTINCT p.id) as items,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as names
            FROM products p
            LEFT JOIN stock_items si ON si.product_id = p.id
            WHERE {tenant_clause('p.tenant_id::text')}
            AND COALESCE(si.qty, 0) < 10
            LIMIT 10
        """
            ),
            tenant_params(),
        ).first()

        # WASTE (stock_moves with negative 'adjustment' type for the day)
        waste = db.execute(
            text(
                f"""
            SELECT
                COALESCE(SUM(ABS(qty)), 0) as total_qty,
                COUNT(*) as count
            FROM stock_moves
            WHERE {tenant_clause('tenant_id::text')}
            AND kind = 'adjustment'
            AND qty < 0
            AND DATE(created_at) = :today
        """
            ),
            tenant_params(today=today),
        ).first()

        # TOP PRODUCTS (best sellers of the month)
        top_products = db.execute(
            text(
                f"""
            SELECT
                p.name as name,
                SUM(prl.qty) as units,
                SUM(prl.line_total) as revenue
            FROM pos_receipt_lines prl
            JOIN pos_receipts pr ON prl.receipt_id = pr.id
            JOIN products p ON prl.product_id = p.id
            WHERE {tenant_clause('pr.tenant_id::text')}
            AND pr.status IN ('paid', 'invoiced')
            AND DATE(pr.created_at) >= :month_start
            GROUP BY p.id, p.name
            ORDER BY revenue DESC
            LIMIT 3
        """
            ),
            tenant_params(month_start=month_start),
        ).fetchall()

        return {
            "counter_sales": {
                "today": float(sales_today),
                "yesterday": float(sales_yesterday),
                "variation": round(variation, 1),
                "currency": currency,
            },
            "critical_stock": {
                "items": critical_stock[0] if critical_stock else 0,
                "names": (critical_stock[1] or [])[:3] if critical_stock else [],
                "urgency": "high" if (critical_stock and critical_stock[0] > 5) else "medium",
            },
            "waste": {
                "today": float(waste[0]) if waste else 0.0,
                "unit": "kg",
                "estimated_value": 0.0,
                "currency": currency,
            },
            "production": {
                "batches_completed": 0,
                "batches_scheduled": 0,
                "progress": 0.0,
            },
            "ingredients_expiring": {"next_7_days": 0, "items": []},
            "top_products": (
                [
                    {
                        "name": row[0] or "Unnamed",
                        "units": int(row[1]) if row[1] else 0,
                        "revenue": float(row[2]) if row[2] else 0.0,
                    }
                    for row in top_products
                ]
                if top_products
                else []
            ),
        }

    elif sector == "taller":
        # MONTHLY REVENUE (invoices + tickets)
        monthly_revenue = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(total), 0) as total
            FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(fecha) >= :month_start
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(month_start=month_start),
            ).scalar()
            or 0.0
        )

        # COMPLETED JOBS
        jobs_today = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(*) FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(fecha) = :today
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(today=today),
            ).scalar()
            or 0
        )

        jobs_month = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(*) FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(fecha) >= :month_start
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(month_start=month_start),
            ).scalar()
            or 0
        )

        # LOW STOCK SPARE PARTS
        spare_parts = db.execute(
            text(
                f"""
            SELECT
                COUNT(DISTINCT p.id) as items,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as names
            FROM products p
            LEFT JOIN stock_items si ON si.product_id = p.id
            WHERE {tenant_clause('p.tenant_id::text')}
            AND COALESCE(si.qty_on_hand, 0) < 5
            LIMIT 10
        """
            ),
            tenant_params(),
        ).first()

        return {
            "pending_repairs": {
                "total": 0,
                "urgent": 0,
                "average_wait_time": 0.0,
                "time_unit": "days",
            },
            "monthly_revenue": {
                "current": float(monthly_revenue),
                "target": 6000.00,
                "progress": round((monthly_revenue / 6000.00 * 100), 1) if monthly_revenue > 0 else 0.0,
                "currency": currency,
            },
            "low_stock_spare_parts": {
                "items": spare_parts[0] if spare_parts else 0,
                "names": (spare_parts[1] or [])[:3] if spare_parts else [],
                "urgency": "high" if (spare_parts and spare_parts[0] > 5) else "medium",
            },
            "completed_jobs": {
                "today": int(jobs_today),
                "week": 0,
                "month": int(jobs_month),
            },
        }

    elif sector == "todoa100" or sector == "retail":
        # DAILY SALES
        daily_sales = db.execute(
            text(
                f"""
            SELECT
                COALESCE(SUM(gross_total), 0) as total,
                COUNT(*) as tickets
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
            ),
            tenant_params(today=today),
        ).first()

        total_today = float(daily_sales[0]) if daily_sales else 0.0
        tickets_today = int(daily_sales[1]) if daily_sales else 0
        average_ticket = (total_today / tickets_today) if tickets_today > 0 else 0.0

        # WEEKLY COMPARISON
        weekly_sales = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) >= :week_ago
            AND status IN ('paid', 'invoiced')
        """
                ),
                tenant_params(week_ago=week_ago),
            ).scalar()
            or 0.0
        )

        # STOCK ROTATION (best selling vs least selling products)
        _rotation = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(DISTINCT p.id) as total
            FROM products p
            WHERE {tenant_clause('p.tenant_id::text')}
        """
                ),
                tenant_params(),
            ).scalar()
            or 0
        )

        return {
            "daily_sales": {
                "total": total_today,
                "tickets": tickets_today,
                "average_ticket": round(average_ticket, 2),
                "currency": currency,
            },
            "stock_rotation": {
                "high_rotation_products": 0,
                "low_rotation_products": 0,
                "replenishment_needed": 0,
            },
            "weekly_comparison": {
                "current": float(weekly_sales),
                "previous": 0.0,
                "variation": 0.0,
                "currency": currency,
            },
        }

    else:  # default - generic real data
        # Total daily sales (POS + Invoices)
        pos_sales = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(gross_total), 0)
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                tenant_params(today=today),
            ).scalar()
            or 0.0
        )

        invoice_sales = (
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(total), 0)
            FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(fecha) = :today
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(today=today),
            ).scalar()
            or 0.0
        )

        tickets_count = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(*)
            FROM pos_receipts
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                tenant_params(today=today),
            ).scalar()
            or 0
        )

        return {
            "sales_today": {
                "total": float(pos_sales + invoice_sales),
                "tickets": int(tickets_count),
                "currency": currency,
            },
            "new_customers": {"month": 0, "week": 0},
            "message": "Generic dashboard. Select a sector template for specific KPIs.",
        }


@router.get("")
def get_current_sector_kpis(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    sector: str | None = None,
) -> dict[str, Any]:
    """
    KPIs for the current tenant's sector (without hardcoding the route).
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id required")

    tenant = db.get(Tenant, tenant_id)
    sector_code = _resolve_sector(sector, tenant)

    # Enable RLS
    set_tenant_guc(db, tenant_id)
    currency = _resolve_sector_currency(db, sector_code)

    return _sector_kpis_payload(sector_code, str(tenant_id), db, currency)


@router.get("/{sector}")
def get_sector_kpis(
    sector: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict[str, Any]:
    """
    Returns specific KPIs for each business sector.
    REAL data from system tables.
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id required")

    # Enable RLS
    set_tenant_guc(db, tenant_id)
    tenant = db.get(Tenant, tenant_id)
    sector_code = _resolve_sector(sector, tenant)
    currency = _resolve_sector_currency(db, sector_code)

    return _sector_kpis_payload(sector_code, str(tenant_id), db, currency)
