"""
Contexto del módulo Conciliación para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de conciliación para el contexto del copilot."""
    transactions = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total, coalesce(sum(amount), 0) AS monto "
            "FROM bank_transactions WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY monto DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    reconciliations = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total, coalesce(sum(difference), 0) AS diferencia "
            "FROM bank_reconciliations WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Conciliación",
        "transacciones_bancarias": [dict(r._mapping) for r in transactions],
        "conciliaciones_por_estado": [dict(r._mapping) for r in reconciliations],
    }
