"""
Finance module context for the copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Return the current finance summary for the copilot context."""
    bank_summary = db.execute(
        text(
            "SELECT type::text AS type, count(*) AS count, coalesce(sum(amount), 0) AS total "
            "FROM bank_transactions WHERE tenant_id = :tid "
            "GROUP BY type ORDER BY total DESC"
        ),
        {"tid": tenant_id},
    ).fetchall()

    return {
        "module": "Finance",
        "bank_summary": [dict(r._mapping) for r in bank_summary],
    }
