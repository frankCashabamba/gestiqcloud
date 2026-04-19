"""
Contexto del módulo CRM para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual del CRM para el contexto del copilot."""
    leads = db.execute(
        text(
            "SELECT status::text AS estado, count(*) AS total "
            "FROM crm_leads WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    opportunities = db.execute(
        text(
            "SELECT stage::text AS etapa, count(*) AS total, coalesce(sum(value), 0) AS valor "
            "FROM crm_opportunities WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY valor DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "CRM",
        "leads_por_estado": [dict(r._mapping) for r in leads],
        "oportunidades_por_etapa": [dict(r._mapping) for r in opportunities],
    }
