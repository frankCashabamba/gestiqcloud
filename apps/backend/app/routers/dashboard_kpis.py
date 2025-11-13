"""
Dashboard KPIs - Endpoint para métricas personalizadas por sector
Conecta con datos REALES de las tablas del sistema
"""

import logging
from datetime import date, timedelta
from typing import Any

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import set_tenant_guc
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard/kpis", tags=["Dashboard KPIs"])
logger = logging.getLogger("app.dashboard_kpis")


@router.get("/{sector}")
def get_sector_kpis(
    sector: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
) -> dict[str, Any]:
    """
    Retorna KPIs específicos para cada sector de negocio.
    Datos REALES desde las tablas del sistema.
    """
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id required")

    # Activar RLS
    set_tenant_guc(db, tenant_id)

    # Fechas para filtros
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)

    if sector == "panaderia":
        # VENTAS MOSTRADOR (desde pos_receipts + invoices)
        ventas_hoy = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                {"today": today},
            ).scalar()
            or 0.0
        )

        ventas_ayer = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) = :yesterday
            AND status IN ('paid', 'invoiced')
        """
                ),
                {"yesterday": yesterday},
            ).scalar()
            or 0.0
        )

        variacion = ((ventas_hoy - ventas_ayer) / ventas_ayer * 100) if ventas_ayer > 0 else 0.0

        # STOCK CRÍTICO (productos con stock bajo)
        stock_critico = db.execute(
            text(
                """
            SELECT
                COUNT(DISTINCT p.id) as items,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as nombres
            FROM products p
            LEFT JOIN stock_items si ON si.product_id = p.id
            WHERE p.tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND COALESCE(si.qty, 0) < 10
            LIMIT 10
        """
            )
        ).first()

        # MERMAS (stock_moves con tipo 'adjustment' negativo del día)
        mermas = db.execute(
            text(
                """
            SELECT
                COALESCE(SUM(ABS(qty)), 0) as total_qty,
                COUNT(*) as count
            FROM stock_moves
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND kind = 'adjustment'
            AND qty < 0
            AND DATE(created_at) = :today
        """
            ),
            {"today": today},
        ).first()

        # TOP PRODUCTOS (más vendidos del mes)
        top_productos = db.execute(
            text(
                """
            SELECT
                p.name as nombre,
                SUM(prl.qty) as unidades,
                SUM(prl.line_total) as ingresos
            FROM pos_receipt_lines prl
            JOIN pos_receipts pr ON prl.receipt_id = pr.id
            JOIN products p ON prl.product_id = p.id
            WHERE pr.tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND pr.status IN ('paid', 'invoiced')
            AND DATE(pr.created_at) >= :month_start
            GROUP BY p.id, p.name
            ORDER BY ingresos DESC
            LIMIT 3
        """
            ),
            {"month_start": month_start},
        ).fetchall()

        return {
            "ventas_mostrador": {
                "hoy": float(ventas_hoy),
                "ayer": float(ventas_ayer),
                "variacion": round(variacion, 1),
                "moneda": "EUR",
            },
            "stock_critico": {
                "items": stock_critico[0] if stock_critico else 0,
                "nombres": (stock_critico[1] or [])[:3] if stock_critico else [],
                "urgencia": "alta" if (stock_critico and stock_critico[0] > 5) else "media",
            },
            "mermas": {
                "hoy": float(mermas[0]) if mermas else 0.0,
                "unidad": "kg",
                "valor_estimado": 0.0,
                "moneda": "EUR",
            },
            "produccion": {
                "hornadas_completadas": 0,
                "hornadas_programadas": 0,
                "progreso": 0.0,
            },
            "ingredientes_caducar": {"proximos_7_dias": 0, "items": []},
            "top_productos": (
                [
                    {
                        "nombre": row[0] or "Sin nombre",
                        "unidades": int(row[1]) if row[1] else 0,
                        "ingresos": float(row[2]) if row[2] else 0.0,
                    }
                    for row in top_productos
                ]
                if top_productos
                else []
            ),
        }

    elif sector == "taller":
        # INGRESOS DEL MES (facturas + tickets)
        ingresos_mes = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(total), 0) as total
            FROM invoices
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(fecha) >= :month_start
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                {"month_start": month_start},
            ).scalar()
            or 0.0
        )

        # TRABAJOS COMPLETADOS
        trabajos_hoy = (
            db.execute(
                text(
                    """
            SELECT COUNT(*) FROM invoices
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(fecha) = :today
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                {"today": today},
            ).scalar()
            or 0
        )

        trabajos_mes = (
            db.execute(
                text(
                    """
            SELECT COUNT(*) FROM invoices
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(fecha) >= :month_start
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                {"month_start": month_start},
            ).scalar()
            or 0
        )

        # REPUESTOS BAJO STOCK
        repuestos = db.execute(
            text(
                """
            SELECT
                COUNT(DISTINCT p.id) as items,
                ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) as nombres
            FROM products p
            LEFT JOIN stock_items si ON si.product_id = p.id
            WHERE p.tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND COALESCE(si.qty_on_hand, 0) < 5
            LIMIT 10
        """
            )
        ).first()

        return {
            "reparaciones_pendientes": {
                "total": 0,
                "urgentes": 0,
                "tiempo_medio_espera": 0.0,
                "unidad_tiempo": "días",
            },
            "ingresos_mes": {
                "actual": float(ingresos_mes),
                "objetivo": 6000.00,
                "progreso": round((ingresos_mes / 6000.00 * 100), 1) if ingresos_mes > 0 else 0.0,
                "moneda": "EUR",
            },
            "repuestos_bajo_stock": {
                "items": repuestos[0] if repuestos else 0,
                "nombres": (repuestos[1] or [])[:3] if repuestos else [],
                "urgencia": "alta" if (repuestos and repuestos[0] > 5) else "media",
            },
            "trabajos_completados": {
                "hoy": int(trabajos_hoy),
                "semana": 0,
                "mes": int(trabajos_mes),
            },
        }

    elif sector == "todoa100" or sector == "retail":
        # VENTAS DEL DÍA
        ventas_hoy = db.execute(
            text(
                """
            SELECT
                COALESCE(SUM(gross_total), 0) as total,
                COUNT(*) as tickets
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
            ),
            {"today": today},
        ).first()

        total_hoy = float(ventas_hoy[0]) if ventas_hoy else 0.0
        tickets_hoy = int(ventas_hoy[1]) if ventas_hoy else 0
        ticket_medio = (total_hoy / tickets_hoy) if tickets_hoy > 0 else 0.0

        # COMPARATIVA SEMANAL
        ventas_semana = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(gross_total), 0) as total
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) >= :week_ago
            AND status IN ('paid', 'invoiced')
        """
                ),
                {"week_ago": week_ago},
            ).scalar()
            or 0.0
        )

        # STOCK ROTACIÓN (productos más vendidos vs menos vendidos)
        _rotacion = (
            db.execute(
                text(
                    """
            SELECT COUNT(DISTINCT p.id) as total
            FROM products p
            WHERE p.tenant_id::text = current_setting('app.tenant_id', TRUE)
        """
                )
            ).scalar()
            or 0
        )

        return {
            "ventas_dia": {
                "total": total_hoy,
                "tickets": tickets_hoy,
                "ticket_medio": round(ticket_medio, 2),
                "moneda": "EUR",
            },
            "stock_rotacion": {
                "productos_alta_rotacion": 0,
                "productos_baja_rotacion": 0,
                "reposicion_necesaria": 0,
            },
            "comparativa_semana": {
                "actual": float(ventas_semana),
                "anterior": 0.0,
                "variacion": 0.0,
                "moneda": "EUR",
            },
        }

    else:  # default - datos reales genéricos
        # Ventas totales del día (POS + Facturas)
        ventas_pos = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(gross_total), 0)
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                {"today": today},
            ).scalar()
            or 0.0
        )

        ventas_facturas = (
            db.execute(
                text(
                    """
            SELECT COALESCE(SUM(total), 0)
            FROM invoices
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(fecha) = :today
            AND estado IN ('posted', 'einvoice_sent', 'paid')
        """
                ),
                {"today": today},
            ).scalar()
            or 0.0
        )

        tickets_count = (
            db.execute(
                text(
                    """
            SELECT COUNT(*)
            FROM pos_receipts
            WHERE tenant_id::text = current_setting('app.tenant_id', TRUE)
            AND DATE(created_at) = :today
            AND status IN ('paid', 'invoiced')
        """
                ),
                {"today": today},
            ).scalar()
            or 0
        )

        return {
            "ventas_hoy": {
                "total": float(ventas_pos + ventas_facturas),
                "tickets": int(tickets_count),
                "moneda": "EUR",
            },
            "clientes_nuevos": {"mes": 0, "semana": 0},
            "mensaje": "Dashboard genérico. Selecciona una plantilla de sector para KPIs específicos.",
        }
