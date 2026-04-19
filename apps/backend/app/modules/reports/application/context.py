"""
Contexto del módulo Reportes para el copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Retorna resumen del estado actual de reportes para el contexto del copilot."""
    sales = db.execute(
        text(
            "SELECT coalesce(sum(total_amount), 0) AS ventas "
            "FROM sales_orders WHERE tenant_id = :tid "
            "AND created_at > CURRENT_DATE - INTERVAL '30 days'"
        ),
        {"tid": tenant_id},
    ).fetchone()

    expenses = db.execute(
        text(
            "SELECT coalesce(sum(amount), 0) AS gastos "
            "FROM expenses WHERE tenant_id = :tid "
            "AND date > CURRENT_DATE - INTERVAL '30 days'"
        ),
        {"tid": tenant_id},
    ).fetchone()

    invoices = db.execute(
        text(
            "SELECT count(*) AS total, coalesce(sum(total), 0) AS facturado "
            "FROM invoices WHERE tenant_id = :tid "
            "AND created_at::timestamp > CURRENT_DATE - INTERVAL '30 days'"
        ),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "modulo": "Reportes",
        "ventas_30d": float(sales[0]) if sales else 0,
        "gastos_30d": float(expenses[0]) if expenses else 0,
        "facturas_30d": {
            "total": int(invoices[0]) if invoices else 0,
            "facturado": float(invoices[1]) if invoices else 0,
        },
    }
