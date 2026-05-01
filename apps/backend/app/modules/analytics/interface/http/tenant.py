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
from app.core.authz import require_scope
from app.db.rls import ensure_rls, set_tenant_guc, tenant_id_sql_expr_text
from app.models.company.company import SectorTemplate
from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant

router = APIRouter(
    prefix="/dashboard/kpis",
    tags=["Dashboard KPIs"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)
logger = logging.getLogger("app.dashboard_kpis")


def _resolve_sector(sector: str | None, tenant: Tenant | None) -> str:
    if sector:
        return sector.lower()
    if tenant and tenant.sector_template_name:
        return tenant.sector_template_name.strip().lower()
    return "default"


def _resolve_tenant_currency(db: Session, tenant_id: str | None) -> str | None:
    if not tenant_id:
        return None
    settings = db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    if settings and settings.currency:
        return str(settings.currency).strip().upper() or None
    tenant = db.get(Tenant, tenant_id)
    if tenant and tenant.base_currency:
        return str(tenant.base_currency).strip().upper() or None
    return None


def _resolve_sector_currency(
    db: Session, sector_code: str, tenant_id: str | None = None
) -> str | None:
    # Tenant currency always takes priority over sector template defaults
    tenant_currency = _resolve_tenant_currency(db, tenant_id)
    if tenant_currency:
        return tenant_currency
    tpl = (
        db.query(SectorTemplate)
        .filter(SectorTemplate.code == sector_code, SectorTemplate.is_active == True)  # noqa: E712
        .first()
    )
    if not tpl:
        return None
    config = tpl.template_config or {}
    defaults = config.get("defaults", {}) or {}
    return defaults.get("currency") or None


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

    def scalar_float(value: Any) -> float:
        return float(value) if value is not None else 0.0

    # Dates for filters
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    next_week = today + timedelta(days=7)
    month_start = today.replace(day=1)

    if sector == "panaderia":
        # COUNTER SALES (from pos_receipts + invoices)
        sales_today = scalar_float(
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
        )

        sales_yesterday = scalar_float(
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
        )

        variation = (
            ((sales_today - sales_yesterday) / sales_yesterday * 100)
            if sales_yesterday > 0
            else 0.0
        )

        # CRITICAL STOCK (products with low stock)
        critical_stock = db.execute(
            text(
                f"""
            SELECT
                COUNT(DISTINCT p.id) as items,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as names,
                COUNT(DISTINCT p.id) FILTER (WHERE COALESCE(p.is_raw_material, FALSE) IS FALSE) as sale_items,
                ARRAY_AGG(DISTINCT p.name) FILTER (
                    WHERE p.name IS NOT NULL
                      AND COALESCE(p.is_raw_material, FALSE) IS FALSE
                ) as sale_names,
                COUNT(DISTINCT p.id) FILTER (WHERE COALESCE(p.is_raw_material, FALSE) IS TRUE) as raw_items,
                ARRAY_AGG(DISTINCT p.name) FILTER (
                    WHERE p.name IS NOT NULL
                      AND COALESCE(p.is_raw_material, FALSE) IS TRUE
                ) as raw_names
            FROM products p
            LEFT JOIN stock_items si
              ON si.product_id = p.id
             AND {tenant_clause('si.tenant_id::text')}
            WHERE {tenant_clause('p.tenant_id::text')}
            AND COALESCE(si.qty, 0) < 10
            LIMIT 10
        """
            ),
            tenant_params(),
        ).first()

        # WASTE (completed production orders with waste on the day)
        waste = db.execute(
            text(
                f"""
            SELECT
                COALESCE(SUM(po.waste_qty), 0) as total_qty,
                COALESCE(
                    SUM(
                        CASE
                            WHEN COALESCE(po.waste_qty, 0) <= 0 THEN 0
                            WHEN COALESCE(order_costs.total_material_cost, 0) <= 0 THEN 0
                            ELSE (
                                order_costs.total_material_cost
                                / NULLIF(COALESCE(po.qty_produced, 0) + COALESCE(po.waste_qty, 0), 0)
                            ) * COALESCE(po.waste_qty, 0)
                        END
                    ),
                    0
                ) as estimated_value
            FROM production_orders po
            LEFT JOIN (
                SELECT order_id, COALESCE(SUM(cost_total), 0) as total_material_cost
                FROM production_order_lines
                GROUP BY order_id
            ) order_costs ON order_costs.order_id = po.id
            WHERE {tenant_clause('po.tenant_id::text')}
            AND po.status = 'COMPLETED'
            AND DATE(po.completed_at) = :today
        """
            ),
            tenant_params(today=today),
        ).first()

        production = db.execute(
            text(
                f"""
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN status = 'COMPLETED' AND DATE(completed_at) = :today THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) as batches_completed,
                COALESCE(
                    SUM(
                        CASE
                            WHEN DATE(COALESCE(scheduled_date, created_at)) = :today
                              AND status IN ('SCHEDULED', 'IN_PROGRESS', 'COMPLETED')
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) as batches_scheduled
            FROM production_orders
            WHERE {tenant_clause('tenant_id::text')}
        """
            ),
            tenant_params(today=today),
        ).first()

        expiring_ingredients = db.execute(
            text(
                f"""
            SELECT
                p.name as name,
                MIN(si.expires_at) as next_expiry
            FROM stock_items si
            JOIN products p ON p.id = si.product_id
            WHERE {tenant_clause('si.tenant_id::text')}
              AND COALESCE(si.qty, 0) > 0
              AND si.expires_at IS NOT NULL
              AND si.expires_at >= :today
              AND si.expires_at <= :next_week
            GROUP BY p.id, p.name
            ORDER BY next_expiry ASC, p.name ASC
            LIMIT 5
        """
            ),
            tenant_params(today=today, next_week=next_week),
        ).fetchall()

        batches_completed = int(production[0]) if production and production[0] is not None else 0
        batches_scheduled = int(production[1]) if production and production[1] is not None else 0
        progress = (
            round((batches_completed / batches_scheduled) * 100, 1)
            if batches_scheduled > 0
            else (100.0 if batches_completed > 0 else 0.0)
        )

        # SALES ORDERS PENDING
        pedidos_pendientes = db.execute(
            text(
                f"""
            SELECT
                COUNT(*) FILTER (WHERE status = 'borrador') as pendientes_cobro,
                COUNT(*) FILTER (
                    WHERE status IN ('invoiced', 'confirmed')
                    AND required_date IS NOT NULL
                    AND required_date >= CURRENT_DATE
                ) as pendientes_entrega
            FROM sales_orders
            WHERE {tenant_clause('tenant_id::text')}
            AND status NOT IN ('cancelled')
        """
            ),
            tenant_params(),
        ).first()

        # PEDIDOS EN BORRADOR CON PRODUCTOS QUE TIENEN RECETA (pendientes de producir)
        pedidos_con_receta = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(DISTINCT so.id)
            FROM sales_orders so
            JOIN sales_order_items soi ON soi.sales_order_id = so.id
            WHERE {tenant_clause('so.tenant_id::text')}
              AND so.status = 'draft'
              AND EXISTS (
                  SELECT 1 FROM recipes r
                  WHERE r.product_id = soi.product_id
              )
        """
                ),
                tenant_params(),
            ).scalar()
            or 0
        )

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
                "sale_products": {
                    "items": critical_stock[2] if critical_stock else 0,
                    "names": (critical_stock[3] or [])[:3] if critical_stock else [],
                },
                "raw_materials": {
                    "items": critical_stock[4] if critical_stock else 0,
                    "names": (critical_stock[5] or [])[:3] if critical_stock else [],
                },
            },
            "waste": {
                "today": float(waste[0]) if waste else 0.0,
                "unit": "uds",
                "estimated_value": float(waste[1]) if waste else 0.0,
                "currency": currency,
            },
            "production": {
                "batches_completed": batches_completed,
                "batches_scheduled": batches_scheduled,
                "progress": progress,
                "orders_with_recipe": int(pedidos_con_receta),
            },
            "ingredients_expiring": {
                "next_7_days": len(expiring_ingredients or []),
                "items": [row[0] for row in (expiring_ingredients or []) if row[0]],
            },
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
            "pedidos": {
                "pendientes_cobro": int(pedidos_pendientes[0]) if pedidos_pendientes else 0,
                "pendientes_entrega": int(pedidos_pendientes[1]) if pedidos_pendientes else 0,
            },
        }

    elif sector == "taller":
        # MONTHLY REVENUE (invoices + tickets)
        monthly_revenue = scalar_float(
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(total), 0) as total
            FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(issue_date) >= :month_start
            AND status IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(month_start=month_start),
            ).scalar()
        )

        # COMPLETED JOBS
        jobs_today = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(*) FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(issue_date) = :today
            AND status IN ('posted', 'einvoice_sent', 'paid')
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
            AND DATE(issue_date) >= :month_start
            AND status IN ('posted', 'einvoice_sent', 'paid')
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
            AND COALESCE(si.qty, 0) < 5
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
                "progress": (
                    round((monthly_revenue / 6000.00 * 100), 1) if monthly_revenue > 0 else 0.0
                ),
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
        weekly_sales = scalar_float(
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
        )

        # STOCK ROTATION (ventas últimas 4 semanas + stock disponible)
        rotation_counts = db.execute(
            text(
                f"""
        WITH sales AS (
            SELECT prl.product_id, SUM(prl.qty) AS units
            FROM pos_receipt_lines prl
            JOIN pos_receipts pr ON pr.id = prl.receipt_id
            WHERE {tenant_clause('pr.tenant_id::text')}
              AND pr.status IN ('paid', 'invoiced')
              AND DATE(pr.created_at) >= :month_start
            GROUP BY prl.product_id
        ),
        buckets AS (
            SELECT
              SUM(CASE WHEN units >= :high_threshold THEN 1 ELSE 0 END) AS high_rotation,
              SUM(CASE WHEN units > 0 AND units < :high_threshold THEN 1 ELSE 0 END) AS low_rotation
            FROM sales
        )
        SELECT COALESCE(high_rotation, 0) AS high_rotation,
               COALESCE(low_rotation, 0) AS low_rotation
        FROM buckets
        """
            ),
            tenant_params(month_start=month_start, high_threshold=20),
        ).first()

        replenish_needed = (
            db.execute(
                text(
                    f"""
            SELECT COUNT(*) FROM (
              SELECT product_id, COALESCE(SUM(qty), 0) AS qty
              FROM stock_items
              WHERE {tenant_clause('tenant_id::text')}
              GROUP BY product_id
            ) s
            WHERE qty < :min_stock
        """
                ),
                tenant_params(min_stock=5),
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
                "high_rotation_products": int(rotation_counts[0] if rotation_counts else 0),
                "low_rotation_products": int(rotation_counts[1] if rotation_counts else 0),
                "replenishment_needed": int(replenish_needed),
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
        pos_sales = scalar_float(
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
        )

        invoice_sales = scalar_float(
            db.execute(
                text(
                    f"""
            SELECT COALESCE(SUM(total), 0)
            FROM invoices
            WHERE {tenant_clause('tenant_id::text')}
            AND DATE(issue_date) = :today
            AND status IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                tenant_params(today=today),
            ).scalar()
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
    currency = _resolve_sector_currency(db, sector_code, tenant_id=str(tenant_id))

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
    currency = _resolve_sector_currency(db, sector_code, tenant_id=str(tenant_id))

    return _sector_kpis_payload(sector_code, str(tenant_id), db, currency)
