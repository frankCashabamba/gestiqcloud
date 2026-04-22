"""
Production module context for the copilot.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_context_summary(db: Session, tenant_id: str) -> dict[str, Any]:
    """Return the current production summary for the copilot context."""
    active = db.execute(
        text(
            "SELECT count(*) AS total FROM production_orders "
            "WHERE tenant_id = :tid AND status IN ('in_progress', 'planned')"
        ),
        {"tid": tenant_id},
    ).fetchone()

    return {
        "module": "Production",
        "active_orders": int(active[0]) if active else 0,
    }
