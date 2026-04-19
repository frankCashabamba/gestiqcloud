"""
Contexto del módulo Gastos para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de gastos para el contexto del copilot."""
    monthly = db.execute(
        text(
            "SELECT date_trunc('month', date)::date AS mes, "
            "count(*) AS n, coalesce(sum(amount), 0) AS total "
            "FROM expenses WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Gastos",
        "gastos_por_mes": [dict(r._mapping) for r in monthly],
    }
