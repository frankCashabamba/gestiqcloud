from fastapi import Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.database import get_db


def _to_str(val) -> str | None:
    try:
        if val is None:
            return None
        return str(val)
    except Exception:
        return None


def ensure_rls(
    request: Request,
    db: Session = Depends(get_db),
):
    """Setea variables de sesión de Postgres para políticas RLS.

    Requiere que exista `request.state.access_claims` (p.ej. vía with_access_claims)
    o, en su defecto, `request.state.session` con `tenant_id` y `tenant_user_id`.
    No falla si no hay claims.
    """
    tenant_id = None
    user_id = None

    claims = getattr(request.state, "access_claims", None) or {}
    if isinstance(claims, dict):
        tenant_id = claims.get("tenant_id")
        user_id = claims.get("user_id")

    if tenant_id is None or user_id is None:
        sess = getattr(request.state, "session", {}) or {}
        tenant_id = tenant_id or sess.get("tenant_id")
        user_id = user_id or sess.get("tenant_user_id")

    # Si no hay tenant/user, no setear (admin u open routes)
    t_id = _to_str(tenant_id)
    u_id = _to_str(user_id)
    if t_id is None or u_id is None:
        return

    try:
        # If tenant_id looks like an integer (legacy empresa_id), translate to UUID
        if isinstance(t_id, str) and t_id.isdigit():
            try:
                res = db.execute(text("SELECT id::text FROM public.tenants WHERE empresa_id = :eid"), {"eid": int(t_id)})
                row = res.first()
                if row and row[0]:
                    t_id = row[0]
            except Exception:
                pass

        # Use SET LOCAL so it scopes to the current transaction/request
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(t_id)})
        db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(u_id)})
        # Expose tenant_id in session.info for ORM hooks/utilities
        try:
            db.info["tenant_id"] = str(t_id)
        except Exception:
            pass
    except Exception:
        # No romper la request si falla el SET
        pass

    return db


def tenant_id_sql_expr(param_name: str = "tid") -> str:
    """SQL fragment that resolves tenant_id safely.

    Uses the session GUC when present and falls back to a bound parameter.
    Example usage with SQLAlchemy text():
        text(f"INSERT ... VALUES ({tenant_id_sql_expr()}, :other)")
        db.execute(..., {"tid": tid, "other": 123})
    """
    # Use CAST(:param AS uuid) instead of :param::uuid to ensure SQLAlchemy
    # recognizes the bind parameter reliably across dialects.
    return (
        "COALESCE("
        "NULLIF(current_setting('app.tenant_id', true), '')::uuid, "
        f"CAST(:{param_name} AS uuid)"
        ")"
    )


def tenant_id_from_request(request: Request) -> str | None:
    """Extract tenant_id from request.state access claims or session.

    Returns string UUID when available, else None.
    """
    claims = getattr(request.state, "access_claims", None) or {}
    if isinstance(claims, dict):
        tid = claims.get("tenant_id")
        if tid is not None:
            return str(tid)
    sess = getattr(request.state, "session", {}) or {}
    tid = sess.get("tenant_id")
    return str(tid) if tid is not None else None
