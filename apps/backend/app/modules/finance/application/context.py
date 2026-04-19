"""
Contexto del módulo Finanzas para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de finanzas para el contexto del copilot."""
    bank_summary = db.execute(
        text(
            "SELECT type::text AS tipo, count(*) AS n, coalesce(sum(amount), 0) AS total "
            "FROM bank_transactions WHERE tenant_id = :tid "
            "GROUP BY type ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Finanzas",
        "resumen_bancario": [dict(r._mapping) for r in bank_summary],
    }
