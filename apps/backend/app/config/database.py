# app/config/database.py
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config.settings import settings

Base = declarative_base()


def make_db_url() -> str:
    """
    Usa la URL normalizada de settings.database_url.
    Nota: si necesitas forzar SSL (cloud providers), aÃ±ade `sslmode=require` en tu DATABASE_URL
    o deja esta lÃ³gica activa en prod. Ajusta a tu polÃ­tica.
    """
    url = settings.database_url
    if settings.ENVIRONMENT == "production" and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


# ---------------------------------------------------------------------------
# Engine con pooling, pre_ping y statement_timeout (vÃ­a psycopg/pg options)
# ---------------------------------------------------------------------------
STATEMENT_TIMEOUT_MS = max(1000, settings.DB_STATEMENT_TIMEOUT_MS)  # mÃ­nimo 1s

CONNECT_ARGS = {
    # Requiere driver psycopg (postgresql+psycopg://) para respetar options
    "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
    "client_encoding": "UTF8",
}

_env_db_url = os.getenv("DATABASE_URL")
_env_db_dsn = os.getenv("DB_DSN")
_db_url = make_db_url()
print("[database] ENV DATABASE_URL type=" f"{type(_env_db_url).__name__} repr={_env_db_url!r}")
print("[database] ENV DB_DSN type=" f"{type(_env_db_dsn).__name__} repr={_env_db_dsn!r}")
print(
    "[database] ENV PGHOST="
    f"{os.getenv('PGHOST')!r} PGPORT={os.getenv('PGPORT')!r} "
    f"PGUSER={os.getenv('PGUSER')!r} PGPASSWORD={os.getenv('PGPASSWORD')!r} "
    f"PGSERVICE={os.getenv('PGSERVICE')!r}"
)
print(f"[database] DATABASE_URL type={type(_db_url).__name__} repr={_db_url!r}")

IS_SQLITE = _db_url.startswith("sqlite")
PG_SCHEMA_NAME = "public"
SCHEMA_PREFIX = f"{PG_SCHEMA_NAME}." if not IS_SQLITE else ""


def schema_table_args(**extras):
    args = {"extend_existing": True}
    if not IS_SQLITE:
        args["schema"] = PG_SCHEMA_NAME
    args.update(extras)
    return args


def schema_table_name(table_name: str) -> str:
    return f"{SCHEMA_PREFIX}{table_name}" if table_name else table_name


def schema_column(table_name: str, column: str = "id") -> str:
    base = schema_table_name(table_name)
    return f"{base}.{column}" if column else base


if IS_SQLITE:
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
        pool_pre_ping=True,  # detecta conexiones rotas
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
# Async session shim for tests (patch target)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db_session():  # pragma: no cover - used as patch target in tests
    """
    Async context manager placeholder to satisfy imports in modules that expect
    an async DB session provider. Unit tests patch this symbol with an
    AsyncMock that implements the async context manager protocol.

    In production, use the synchronous dependencies (get_db/session_scope) or
    provide a real AsyncSession provider.
    """
    raise NotImplementedError(
        "get_db_session is a test-time placeholder; patch it or provide an async provider"
    )


# ---------------------------------------------------------------------------
# Dependencia FastAPI: sesiÃ³n por request
# ---------------------------------------------------------------------------
def get_db(request: Request) -> Iterator[Session]:
    """
    Uso:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        # Defensive: clear any leftover GUCs from pooled connections
        # Use set_config(..., NULL, true) instead of RESET to avoid
        # aborting the transaction when the custom GUC was never set.
        try:
            db.execute(text("SELECT set_config('app.tenant_id', NULL, true)"))
            db.execute(text("SELECT set_config('app.user_id', NULL, true)"))
        except Exception:
            # If anything goes wrong, ensure we don't leave the session aborted
            try:
                db.rollback()
            except Exception:
                pass
            pass
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
                # translate legacy tenant_id (digits) -> tenant UUID
                if tid.isdigit():
                    try:
                        res = db.execute(
                            text("SELECT id FROM tenants WHERE tenant_id = :eid"),
                            {"eid": int(tid)},
                        )
                        row = res.first()
                        if row and row[0]:
                            tid = row[0]
                    except Exception:
                        # Ensure we don't leave the session aborted if the lookup fails
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        pass
                db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
                db.execute(text("SET LOCAL app.user_id = :uid"), {"uid": uid})
                # Expose resolved tenant to ORM hooks/utilities on this Session
                try:
                    db.info["tenant_id"] = tid
                except Exception:
                    pass
        except Exception:
            # Do not break request if setting GUCs fails, but clean aborted tx
            try:
                db.rollback()
            except Exception:
                pass
            pass

        # Final safeguard: ensure session isn't in aborted state before yielding
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            try:
                db.rollback()
            except Exception:
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
            if hasattr(obj, "tenant_id") and getattr(obj, "tenant_id", None) in (
                None,
                "",
            ):
                obj.tenant_id = tid
        except Exception:
            # do not block flush
            pass


# ---------------------------------------------------------------------------
# (Opcional) Multitenancy por schema (search_path)
# ---------------------------------------------------------------------------
def set_search_path(db: Session, tenant_schema: str) -> None:
    """
    Fija el search_path por sesiÃ³n. Incluye siempre 'public' como fallback.
    Llamar tras abrir la sesiÃ³n (en una dependencia que resuelva el tenant).
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
    Ãštil para /health.
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
            ...  # commit/rollback automÃ¡tico
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
