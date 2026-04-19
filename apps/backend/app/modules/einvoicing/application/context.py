"""
Contexto del módulo Facturación Electrónica para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de facturación electrónica para el contexto del copilot."""
    sri = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total "
            "FROM sri_submissions WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    sii = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total "
            "FROM sii_batches WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Facturación Electrónica",
        "sri_por_estado": [dict(r._mapping) for r in sri],
        "sii_por_estado": [dict(r._mapping) for r in sii],
    }
