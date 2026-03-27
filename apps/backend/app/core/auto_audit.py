"""
auto_audit.py
=============
Automatic SQLAlchemy auditing via after_flush.

Registers an AuditEvent for created, updated and deleted ORM objects without
requiring endpoint-level changes.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.audit_events import normalize_audit_changes

logger = logging.getLogger("app.auto_audit")

_SKIP_TABLES: frozenset[str] = frozenset(
    {
        "audit_events",
        "auth_audit",
        "notification_logs",
        "sync_conflict_logs",
        "request_logs",
        "alembic_version",
    }
)

_SKIP_FIELDS: frozenset[str] = frozenset(
    {
        "password_hash",
        "password",
        "token",
        "refresh_token",
        "secret",
        "api_key",
        "private_key",
        "updated_at",
        "created_at",
    }
)

_MAX_FIELD_LEN = 500


def _safe_str(value: Any) -> Any:
    """Convert to JSON-safe data and truncate long strings recursively."""
    normalized = normalize_audit_changes(value)
    if normalized is None:
        return None
    if isinstance(normalized, str):
        return normalized[:_MAX_FIELD_LEN] + "..." if len(normalized) > _MAX_FIELD_LEN else normalized
    if isinstance(normalized, dict):
        return {key: _safe_str(item) for key, item in normalized.items()}
    if isinstance(normalized, list):
        return [_safe_str(item) for item in normalized]
    return normalized


def _entity_type(obj: Any) -> str:
    return obj.__class__.__name__


def _entity_id(obj: Any) -> str | None:
    raw = getattr(obj, "id", None)
    if raw is None:
        return None
    return str(raw)


def _should_audit(obj: Any) -> bool:
    table = getattr(getattr(obj, "__class__", None), "__tablename__", None)
    if not table or table in _SKIP_TABLES:
        return False
    try:
        sa_inspect(obj)
    except Exception:
        return False
    return True


def _get_update_changes(obj: Any) -> dict[str, Any]:
    """Return {field: {old: ..., new: ...}} for changed mapped attributes."""
    changes: dict[str, Any] = {}
    try:
        mapper = sa_inspect(obj)
        for attr in mapper.attrs:
            if attr.key in _SKIP_FIELDS:
                continue
            try:
                hist = attr.history
                if not hist.has_changes():
                    continue
                old_val = hist.deleted[0] if hist.deleted else None
                new_val = hist.added[0] if hist.added else None
                if old_val == new_val:
                    continue
                changes[attr.key] = {
                    "old": _safe_str(old_val),
                    "new": _safe_str(new_val),
                }
            except Exception:
                pass
    except Exception:
        pass
    return changes


def _coerce_uuid(value: str | None):
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _build_event(session: Session, action: str, obj: Any, changes: dict | None = None):
    from app.models.core.audit_event import AuditEvent  # noqa: PLC0415

    tenant_id = _coerce_uuid(session.info.get("tenant_id"))
    user_id = _coerce_uuid(session.info.get("user_id"))

    return AuditEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        actor_type="user" if user_id else "system",
        action=action,
        entity_type=_entity_type(obj),
        entity_id=_entity_id(obj),
        source="orm",
        changes=normalize_audit_changes(changes) if changes else None,
    )


def register_auto_audit(session_factory) -> None:
    """Register a single after_flush audit listener for the session factory."""

    @event.listens_for(session_factory, "after_flush")
    def _after_flush(session: Session, flush_context):
        del flush_context
        if session.info.get("_auto_audit_active"):
            return

        events_to_add = []

        try:
            for obj in list(session.new):
                if _should_audit(obj):
                    events_to_add.append(_build_event(session, "create", obj))
        except Exception:
            logger.debug("auto_audit: error processing session.new", exc_info=True)

        try:
            for obj in list(session.dirty):
                if not _should_audit(obj):
                    continue
                changes = _get_update_changes(obj)
                if changes:
                    events_to_add.append(_build_event(session, "update", obj, changes))
        except Exception:
            logger.debug("auto_audit: error processing session.dirty", exc_info=True)

        try:
            for obj in list(session.deleted):
                if _should_audit(obj):
                    events_to_add.append(_build_event(session, "delete", obj))
        except Exception:
            logger.debug("auto_audit: error processing session.deleted", exc_info=True)

        if not events_to_add:
            return

        session.info["_auto_audit_active"] = True
        try:
            for event_row in events_to_add:
                session.add(event_row)
        except Exception:
            logger.warning("auto_audit: error adding events to session", exc_info=True)
        finally:
            session.info["_auto_audit_active"] = False
