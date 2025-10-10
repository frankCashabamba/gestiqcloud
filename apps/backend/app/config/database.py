# app/config/database.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from fastapi import Request

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.config.settings import settings

Base = declarative_base()

def make_db_url() -> str:
    """
    Usa la URL normalizada de settings.database_url.
    Nota: si necesitas forzar SSL (cloud providers), añade `sslmode=require` en tu DATABASE_URL
    o deja esta lógica activa en prod. Ajusta a tu política.
    """
    url = settings.database_url
    if settings.ENV == "production" and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

# ---------------------------------------------------------------------------
# Engine con pooling, pre_ping y statement_timeout (vía psycopg/pg options)
# ---------------------------------------------------------------------------
STATEMENT_TIMEOUT_MS = max(1000, settings.DB_STATEMENT_TIMEOUT_MS)  # mínimo 1s

CONNECT_ARGS = {
    # Requiere driver psycopg (postgresql+psycopg://) para respetar options
    "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}"
}

_db_url = make_db_url()
if _db_url.startswith("sqlite"):
    engine = create_engine(
        _db_url,
        echo=(settings.LOG_LEVEL == "DEBUG"),
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        _db_url,
        pool_size=settings.POOL_SIZE,
        max_overflow=settings.MAX_OVERFLOW,
        pool_timeout=settings.POOL_TIMEOUT,  # segundos
        pool_pre_ping=True,                  # detecta conexiones rotas
        echo=(settings.LOG_LEVEL == "DEBUG"),
        future=True,
        connect_args=CONNECT_ARGS,
    )

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

# ---------------------------------------------------------------------------
# Dependencia FastAPI: sesión por request
# ---------------------------------------------------------------------------
def get_db(request: Request) -> Iterator[Session]:
    """
    Uso:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        # Set RLS GUCs on THIS session using request context
        try:
            claims = getattr(request.state, "access_claims", None) or {}
            sess = getattr(request.state, "session", {}) or {}
            tenant_id = None
            user_id = None
            if isinstance(claims, dict):
                tenant_id = claims.get("tenant_id")
                user_id = claims.get("user_id")
            if tenant_id is None or user_id is None:
                tenant_id = tenant_id or sess.get("tenant_id")
                user_id = user_id or sess.get("tenant_user_id")

            if tenant_id is not None and user_id is not None:
                tid = str(tenant_id)
                uid = str(user_id)
                # translate legacy empresa_id (digits) -> tenant UUID
                if tid.isdigit():
                    try:
                        res = db.execute(text("SELECT id::text FROM public.tenants WHERE empresa_id = :eid"), {"eid": int(tid)})
                        row = res.first()
                        if row and row[0]:
                            tid = row[0]
                    except Exception:
                        pass
                db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
                db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": uid})
        except Exception:
            # Do not break request if setting GUCs fails
            pass

        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# ORM hook: auto-fill tenant_id and UUID PKs when missing (best-effort)
# ---------------------------------------------------------------------------
@event.listens_for(SessionLocal, "before_flush")
def _auto_fill_multitenant_fields(session: Session, flush_context, instances):
    try:
        tid = session.info.get("tenant_id")
    except Exception:
        tid = None
    if not tid:
        return
    for obj in list(session.new):
        try:
            if hasattr(obj, "tenant_id") and getattr(obj, "tenant_id", None) in (None, ""):
                setattr(obj, "tenant_id", tid)
        except Exception:
            # do not block flush
            pass

# ---------------------------------------------------------------------------
# (Opcional) Multitenancy por schema (search_path)
# ---------------------------------------------------------------------------
def set_search_path(db: Session, tenant_schema: str) -> None:
    """
    Fija el search_path por sesión. Incluye siempre 'public' como fallback.
    Llamar tras abrir la sesión (en una dependencia que resuelva el tenant).
    """
    db.execute(text("SET search_path TO :schema, public").bindparams(schema=tenant_schema))

def get_tenant_db(tenant_schema: str) -> Iterator[Session]:
    """
    Dependencia alternativa si ya resolviste tenant_schema (subdominio o X-Tenant).
    Uso:
        db: Session = Depends(lambda: get_tenant_db(schema))
    """
    db = SessionLocal()
    try:
        set_search_path(db, tenant_schema)
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Utilidades: health y scope transaccional
# ---------------------------------------------------------------------------
def ping() -> bool:
    """
    Verifica conectividad y (si es posible) el statement_timeout actual.
    Útil para /health.
    """
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        try:
            db.execute(text("SHOW statement_timeout")).scalar_one()
        except Exception:
            pass
    return True

@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Context manager de conveniencia:
        with session_scope() as db:
            ...  # commit/rollback automático
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
