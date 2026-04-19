"""
Contexto del módulo Usuarios para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de usuarios para el contexto del copilot."""
    stats = db.execute(
        text(
            "SELECT count(*) AS total, "
            "count(*) FILTER (WHERE is_active = true) AS activos, "
            "count(*) FILTER (WHERE is_company_admin = true) AS admins "
            "FROM company_users WHERE tenant_id = :tid"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT first_name, last_name, email, is_active, is_company_admin, created_at "
            "FROM company_users WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    roles = db.execute(
        text("SELECT count(*) AS total FROM company_roles WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "modulo": "Usuarios",
        "usuarios": {
            "total": int(stats[0]) if stats else 0,
            "activos": int(stats[1]) if stats else 0,
            "admins": int(stats[2]) if stats else 0,
        },
        "roles": int(roles[0]) if roles else 0,
        "ultimos_usuarios": [dict(r._mapping) for r in recent],
    }
