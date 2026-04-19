"""
Contexto del módulo Contabilidad para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de contabilidad para el contexto del copilot."""
    statuses = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total, "
            "coalesce(sum(debit_total), 0) AS debito "
            "FROM journal_entries WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    recent = db.execute(
        text(
            "SELECT number, date, status::text AS status, debit_total, credit_total "
            "FROM journal_entries WHERE tenant_id = :tid "
            "ORDER BY date DESC, created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Contabilidad",
        "asientos_por_estado": [dict(r._mapping) for r in statuses],
        "ultimos_asientos": [dict(r._mapping) for r in recent],
    }
