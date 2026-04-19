"""
Contexto del módulo RRHH para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de RRHH para el contexto del copilot."""
    employees = db.execute(
        text(
            "SELECT count(*) AS total FROM employees " "WHERE tenant_id = :tid AND is_active = true"
        ),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "modulo": "RRHH",
        "empleados_activos": int(employees[0]) if employees else 0,
    }
