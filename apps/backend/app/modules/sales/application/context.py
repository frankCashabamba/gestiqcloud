"""
Contexto del módulo Ventas para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de ventas para el contexto del copilot."""
    monthly = db.execute(
        text(
            "SELECT date_trunc('month', created_at)::date AS mes, "
            "count(*) AS pedidos, coalesce(sum(total), 0) AS total "
            "FROM sales_orders WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY 1 DESC LIMIT 6"
        ),
        {"tid": tenant_id},
    ).fetchall()

    top_clients = db.execute(
        text(
            "SELECT c.name, count(*) AS pedidos, coalesce(sum(so.total), 0) AS total "
            "FROM sales_orders so "
            "JOIN clients c ON c.id = so.customer_id "
            "WHERE so.tenant_id = :tid "
            "GROUP BY c.name ORDER BY total DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Ventas",
        "ventas_por_mes": [dict(r._mapping) for r in monthly],
        "top_clientes": [dict(r._mapping) for r in top_clients],
    }
