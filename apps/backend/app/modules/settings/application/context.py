"""
Contexto del módulo Configuración para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de configuración para el contexto del copilot."""
    tenant = db.execute(
        text("SELECT name, sector, country, currency FROM tenants WHERE id = :tid"),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "modulo": "Configuración",
        "tenant": dict(tenant._mapping) if tenant else None,
    }
