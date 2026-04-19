"""
Contexto del módulo POS para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual del POS para el contexto del copilot."""
    shift = db.execute(
        text(
            "SELECT id, status, opened_at, opening_float FROM pos_shifts "
            "WHERE tenant_id = :tid AND status = 'open' ORDER BY opened_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()

    sales = db.execute(
        text(
            "SELECT count(*) AS recibos, coalesce(sum(gross_total),0) AS total "
            "FROM pos_receipts WHERE tenant_id = :tid AND created_at::date = CURRENT_DATE"
        ),
        {"tid": tenant_id},
    ).fetchone()

    top = db.execute(
        text(
            "SELECT p.name, sum(rl.qty) AS qty, sum(rl.line_total) AS total "
            "FROM pos_receipt_lines rl JOIN products p ON p.id = rl.product_id "
            "JOIN pos_receipts r ON r.id = rl.receipt_id "
            "WHERE r.tenant_id = :tid AND r.created_at::date = CURRENT_DATE "
            "GROUP BY p.name ORDER BY total DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "POS",
        "turno_activo": dict(shift._mapping) if shift else None,
        "ventas_hoy": dict(sales._mapping) if sales else {},
        "top_productos_hoy": [dict(r._mapping) for r in top],
    }
