"""
Contexto del módulo Proveedores para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de proveedores para el contexto del copilot."""
    stats = db.execute(
        text(
            "SELECT count(*) AS total, "
            "count(*) FILTER (WHERE is_active = true) AS activos "
            "FROM suppliers WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT name, email, phone, created_at "
            "FROM suppliers WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Proveedores",
        "total_proveedores": int(stats[0]) if stats else 0,
        "proveedores_activos": int(stats[1]) if stats else 0,
        "ultimos_proveedores": [dict(r._mapping) for r in recent],
    }
