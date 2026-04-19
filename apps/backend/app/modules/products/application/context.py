"""
Contexto del módulo Productos para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de productos para el contexto del copilot."""
    stats = db.execute(
        text(
            "SELECT count(*) AS total, "
            "count(*) FILTER (WHERE active = true) AS activos "
            "FROM products WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "modulo": "Productos",
        "total_productos": int(stats[0]) if stats else 0,
        "productos_activos": int(stats[1]) if stats else 0,
    }
