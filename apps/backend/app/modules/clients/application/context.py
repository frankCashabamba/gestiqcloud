"""
Contexto del módulo Clientes para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de clientes para el contexto del copilot."""
    stats = db.execute(
        text(
            "SELECT count(*) AS total, "
            "count(*) FILTER (WHERE is_wholesale = true) AS mayoristas "
            "FROM clients WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT name, city, email, phone "
            "FROM clients WHERE tenant_id = :tid "
            "ORDER BY id DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Clientes",
        "total_clientes": int(stats[0]) if stats else 0,
        "clientes_mayoristas": int(stats[1]) if stats else 0,
        "ultimos_clientes": [dict(r._mapping) for r in recent],
    }
