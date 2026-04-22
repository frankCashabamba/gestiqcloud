"""
Invoicing module context for the copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Return the current invoicing summary for the copilot context."""
    statuses = db.execute(
        text(
            "SELECT status AS status, count(*) AS total, coalesce(sum(total), 0) AS total_amount "
            "FROM invoices WHERE tenant_id = :tid "
            "GROUP BY 1 ORDER BY total_amount DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    recent = db.execute(
        text(
            "SELECT number, supplier, total, status, created_at "
            "FROM invoices WHERE tenant_id = :tid "
            "ORDER BY created_at DESC LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "module": "Invoicing",
        "invoices_by_status": [dict(r._mapping) for r in statuses],
        "recent_invoices": [dict(r._mapping) for r in recent],
    }
