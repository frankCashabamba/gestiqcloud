"""
Contexto del módulo Notificaciones para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de notificaciones para el contexto del copilot."""
    unread = db.execute(
        text(
            "SELECT count(*) AS total FROM notifications "
            "WHERE tenant_id = :tid AND read_at IS NULL AND archived_at IS NULL"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT channel, subject, priority, status, created_at "
            "FROM notifications WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Notificaciones",
        "notificaciones_no_leidas": int(unread[0]) if unread else 0,
        "ultimas_notificaciones": [dict(r._mapping) for r in recent],
    }
