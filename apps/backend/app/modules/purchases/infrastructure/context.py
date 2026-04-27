"""Context summary for the Purchases module."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Return a summary of the current purchases state for the copilot context."""
    pending = db.execute(
        text(
            "SELECT count(*) AS total, coalesce(sum(total_amount), 0) AS amount "
            "FROM purchase_orders WHERE tenant_id = :tid AND status IN ('draft', 'sent', 'confirmed')"
        ),
        {"tid": tenant_id},
    ).fetchone()

    recent = db.execute(
        text(
            "SELECT po.id, s.name AS supplier_name, po.total_amount, po.status, po.created_at "
            "FROM purchase_orders po "
            "LEFT JOIN suppliers s ON s.id = po.supplier_id "
            "WHERE po.tenant_id = :tid "
            "ORDER BY po.created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "modulo": "Compras",
        "pending_orders": dict(pending._mapping) if pending else {},
        "recent_orders": [dict(r._mapping) for r in recent],
    }
