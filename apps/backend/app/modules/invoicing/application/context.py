"""
Contexto del módulo Facturación para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de facturación para el contexto del copilot."""
    statuses = db.execute(
        text(
            "SELECT status AS estado, count(*) AS total, coalesce(sum(total), 0) AS monto "
            "FROM invoices WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY monto DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    recent = db.execute(
        text(
            "SELECT number, supplier, total, status, created_at "
            "FROM invoices WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Facturación",
        "facturas_por_estado": [dict(r._mapping) for r in statuses],
        "ultimas_facturas": [dict(r._mapping) for r in recent],
    }
