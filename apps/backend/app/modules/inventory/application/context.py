"""
Contexto del módulo Inventario para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual del inventario para el contexto del copilot."""
    low_stock = db.execute(
        text(
            "SELECT p.name, si.qty, w.code AS almacen "
            "FROM stock_items si "
            "JOIN products p ON p.id = si.product_id "
            "JOIN warehouses w ON w.id = si.warehouse_id "
            "WHERE si.tenant_id = :tid AND si.qty < 5 "
            "ORDER BY si.qty ASC LIMIT 10"
        ),
        {"tid": tenant_id},
    ).fetchall()

    total_value = db.execute(
        text(
            "SELECT coalesce(sum(on_hand_qty * avg_cost), 0) AS valor "
            "FROM inventory_cost_state WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    ).fetchone()

    no_movement = db.execute(
        text(
            "SELECT p.name, si.qty "
            "FROM stock_items si "
            "JOIN products p ON p.id = si.product_id "
            "WHERE si.tenant_id = :tid AND si.qty > 0 "
            "AND si.product_id NOT IN ("
            "  SELECT DISTINCT product_id FROM stock_moves "
            "  WHERE tenant_id = :tid AND occurred_at > CURRENT_DATE - INTERVAL '30 days'"
            ") LIMIT 10"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Inventario",
        "stock_bajo": [dict(r._mapping) for r in low_stock],
        "valor_total_inventario": float(total_value[0]) if total_value else 0,
        "sin_movimiento_30d": [dict(r._mapping) for r in no_movement],
    }
