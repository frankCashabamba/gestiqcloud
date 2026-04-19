"""
Contexto del módulo Compras para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de compras para el contexto del copilot."""
    pending = db.execute(
        text(
            "SELECT count(*) AS total, coalesce(sum(total_amount), 0) AS monto "
            "FROM purchase_orders WHERE tenant_id = :tid AND status IN ('draft', 'sent', 'confirmed')"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT po.id, s.name AS proveedor, po.total_amount, po.status, po.created_at "
            "FROM purchase_orders po "
            "LEFT JOIN suppliers s ON s.id = po.supplier_id "
            "WHERE po.tenant_id = :tid "
            "ORDER BY po.created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Compras",
        "ordenes_pendientes": dict(pending._mapping) if pending else {},
        "ultimas_ordenes": [dict(r._mapping) for r in recent],
    }
