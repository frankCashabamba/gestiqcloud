from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.sql import literal_column

from app.config.database import get_db


__all__ = [
    "ensure_rls",
    "tenant_id_sql_expr",
    "tenant_id_sql_expr_text",
    "tenant_id_from_request",
    "set_tenant_guc",
    "ensure_guc_from_request",
]


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
        # Si tenant_id parece entero (legacy tenant_id), tradúcelo a UUID
        if isinstance(t_id, str) and t_id.isdigit():
            try:
                # Translate legacy tenant_id (int) to tenant UUID
                res = db.execute(
                    text("SELECT id::text FROM public.tenants WHERE tenant_id = :eid"),
                    {"eid": int(t_id)},
                )
                row = res.first()
                if row and row[0]:
                    t_id = row[0]
                else:
                    import logging

                    logging.warning(f"No tenant found for tenant_id = {t_id}")
            except Exception as e:
                import logging

                logging.warning(f"Error converting tenant_id to tenant_id: {e}")

        # Usa SET LOCAL para scope de transacción/request
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(t_id)})
        db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(u_id)})

        # Expón tenant_id en session.info para hooks/utilidades ORM
        try:
            db.info["tenant_id"] = str(t_id)
        except Exception:
            pass
    except Exception as e:
        # No romper la request si falla el SET, pero log el error
        import logging

        logging.error(f"RLS setup failed: {e}")

    return db


# --- Helpers de expresión para tenant_id ---


def tenant_id_sql_expr():
    """
    Devuelve una EXPRESIÓN SQLAlchemy que lee el tenant desde la GUC.
    Úsala así:
        db.scalar(select(tenant_id_sql_expr()))
        stmt = select(Model).where(Model.tenant_id == tenant_id_sql_expr())
    """
    return literal_column("current_setting('app.tenant_id', true)::uuid").label(
        "tenant_id"
    )


def tenant_id_sql_expr_text(param_name: str = "tid") -> str:
    """
    Devuelve un FRAGMENTO DE TEXTO SQL para usar con sqlalchemy.text().
    Úsalo así:
        text(f\"INSERT ... VALUES ({tenant_id_sql_expr_text()}, :other)\")
        db.execute(..., {\"tid\": tid, \"other\": 123})
    """
    # Preferimos CAST(:param AS uuid) para bind params portables.
    return (
        "COALESCE("
        "NULLIF(current_setting('app.tenant_id', true), '')::uuid, "
        f"CAST(:{param_name} AS uuid)"
        ")"
    )


def tenant_id_from_request(request: Request) -> str | None:
    """Extrae tenant_id desde claims o session en la request.

    Devuelve UUID en string cuando está disponible, si no devuelve None.
    """
    claims = getattr(request.state, "access_claims", None) or {}
    if isinstance(claims, dict):
        tid = claims.get("tenant_id")
        if tid is not None:
            return str(tid)
    sess = getattr(request.state, "session", {}) or {}
    tid = sess.get("tenant_id")
    return str(tid) if tid is not None else None


def set_tenant_guc(db: Session, tenant_id: str, persist: bool = False) -> None:
    """Set tenant GUC en esta sesión de DB.

    - persist=False → SET LOCAL (scope a la transacción actual)
    - persist=True  → SET (persiste en la conexión)
    """
    if not tenant_id:
        return
    try:
        if persist:
            db.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
        else:
            db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        try:
            db.info["tenant_id"] = str(tenant_id)
        except Exception:
            pass
    except Exception:
        pass


def ensure_guc_from_request(
    request: Request, db: Session, persist: bool = False
) -> None:
    """Extrae tenant de la request y lo setea como GUC en esta sesión."""
    tid = tenant_id_from_request(request)
    if tid:
        set_tenant_guc(db, tid, persist=persist)
