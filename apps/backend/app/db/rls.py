from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql import literal_column

from app.config.database import get_db

__all__ = [
    "ensure_rls",
    "tenant_id_sql_expr",
    "tenant_id_guc_expr_text",
    "tenant_id_sql_expr_text",
    "tenant_id_from_request",
    "set_tenant_guc",
    "ensure_guc_from_request",
]


def ensure_rls(
    request: Request,
    db: Session = Depends(get_db),
):
    """Setea variables de sesión de Postgres para políticas RLS.

    Resuelve tenant/usuario por la única puerta `get_tenant_context` (claims o,
    en su defecto, session legacy). Falla si la ruta exige RLS pero no hay
    tenant/user para setear.
    """
    from app.core.tenant_context import get_tenant_context

    ctx = get_tenant_context(request)
    t_id = str(ctx.tenant_id) if ctx.tenant_id else None
    u_id = str(ctx.user_id) if ctx.user_id else None
    if t_id is None or u_id is None:
        raise HTTPException(status_code=401, detail="RLS tenant/user context missing")

    try:
        # SET LOCAL (scope de transacción/request); solo en PostgreSQL.
        try:
            from app.config.database import IS_SQLITE

            if not IS_SQLITE:
                db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t_id})
                db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": u_id})
        except Exception:
            pass

        # Expón el contexto en session.info para hooks/utilidades ORM (after_begin).
        try:
            db.info["tenant_id"] = t_id
            db.info["user_id"] = u_id
        except Exception:
            pass
    except Exception as e:
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
    return literal_column("current_setting('app.tenant_id', true)::uuid").label("tenant_id")


def tenant_id_guc_expr_text() -> str:
    """
    Devuelve un FRAGMENTO DE TEXTO SQL que lee el tenant solo desde la GUC.

    Úsalo en DDL/políticas RLS, donde no queremos introducir bind params
    de fallback ni fijar un tenant concreto en tiempo de creación.
    """
    return "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


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
    """Extrae tenant_id (string) desde el tenant context único.

    Devuelve UUID en string cuando está disponible, si no devuelve None.
    Delega en `get_tenant_context` (claims o, en su defecto, session legacy).
    """
    from app.core.tenant_context import get_tenant_context

    ctx = get_tenant_context(request)
    return str(ctx.tenant_id) if ctx.tenant_id is not None else None


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


def ensure_guc_from_request(request: Request, db: Session, persist: bool = False) -> None:
    """Extrae tenant de la request y lo setea como GUC en esta sesión."""
    tid = tenant_id_from_request(request)
    if tid:
        set_tenant_guc(db, tid, persist=persist)
