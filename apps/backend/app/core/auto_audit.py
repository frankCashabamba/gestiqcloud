"""
auto_audit.py
=============
Auditoría automática vía SQLAlchemy after_flush.

Registra un AuditEvent por cada objeto creado, actualizado o eliminado
en CUALQUIER modelo, sin necesidad de modificar los endpoints.

Contexto (tenant_id, user_id) se lee de session.info, que get_db() ya puebla
a partir del JWT del request.

Tablas excluidas (para evitar recursión y ruido):
  - audit_events, auth_audit — las propias tablas de auditoría
  - notification_logs, sync_conflict_logs — ya son registros de eventos
  - Cualquier tabla cuyo modelo no tenga campo `id`

Campos excluidos de `changes` en updates:
  - password_hash, token, secret, api_key, private_key — seguridad
  - updated_at, created_at — ruido
  - Campos > 500 chars — truncados a 500
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.orm import Session

logger = logging.getLogger("app.auto_audit")

# ---------------------------------------------------------------------------
# Tablas que NO se auditan (nombres de __tablename__)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Campos que se omiten en el diff de cambios (seguridad / ruido)
# ---------------------------------------------------------------------------
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

_MAX_FIELD_LEN = 500  # caracteres máximos por valor en changes


def _safe_str(value: Any) -> Any:
    """Convierte a string truncado si es demasiado largo."""
    if value is None:
        return None
    if isinstance(value, (str,)) and len(value) > _MAX_FIELD_LEN:
        return value[:_MAX_FIELD_LEN] + "…"
    if isinstance(value, (dict, list)):
        s = str(value)
        return s[:_MAX_FIELD_LEN] + "…" if len(s) > _MAX_FIELD_LEN else s
    return value


def _entity_type(obj: Any) -> str:
    return obj.__class__.__name__


def _entity_id(obj: Any) -> str | None:
    raw = getattr(obj, "id", None)
    if raw is None:
        return None
    return str(raw)


def _should_audit(obj: Any) -> bool:
    table = getattr(getattr(obj, "__class__", None), "__tablename__", None)
    if not table:
        return False
    if table in _SKIP_TABLES:
        return False
    # Solo auditamos objetos con mapper (ORM declarativo)
    try:
        sa_inspect(obj)
    except Exception:
        return False
    return True


def _get_update_changes(obj: Any) -> dict[str, Any]:
    """Retorna {campo: {old: ..., new: ...}} para los atributos modificados."""
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
    """Convierte string a UUID, o devuelve None."""
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _build_event(session: Session, action: str, obj: Any, changes: dict | None = None):
    """Construye un AuditEvent ORM sin importarlo al inicio del módulo."""
    # Import diferido para evitar circular imports en startup
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
        changes=changes or None,
    )


# ---------------------------------------------------------------------------
# Listener principal: registrado sobre SessionLocal en database.py
# ---------------------------------------------------------------------------
def register_auto_audit(session_factory) -> None:
    """
    Llama una sola vez desde database.py (o main.py) para registrar el listener.

    Uso:
        from app.core.auto_audit import register_auto_audit
        register_auto_audit(SessionLocal)
    """

    @event.listens_for(session_factory, "after_flush")
    def _after_flush(session: Session, flush_context):
        # Guard anti-recursión: evita auditar los propios AuditEvents
        if session.info.get("_auto_audit_active"):
            return

        events_to_add = []

        try:
            for obj in list(session.new):
                if _should_audit(obj):
                    events_to_add.append(_build_event(session, "create", obj))
        except Exception:
            logger.debug("auto_audit: error procesando session.new", exc_info=True)

        try:
            for obj in list(session.dirty):
                if not _should_audit(obj):
                    continue
                changes = _get_update_changes(obj)
                if changes:
                    events_to_add.append(_build_event(session, "update", obj, changes))
        except Exception:
            logger.debug("auto_audit: error procesando session.dirty", exc_info=True)

        try:
            for obj in list(session.deleted):
                if _should_audit(obj):
                    events_to_add.append(_build_event(session, "delete", obj))
        except Exception:
            logger.debug("auto_audit: error procesando session.deleted", exc_info=True)

        if not events_to_add:
            return

        session.info["_auto_audit_active"] = True
        try:
            for ev in events_to_add:
                session.add(ev)
        except Exception:
            logger.warning("auto_audit: error añadiendo eventos a sesión", exc_info=True)
        finally:
            session.info["_auto_audit_active"] = False
