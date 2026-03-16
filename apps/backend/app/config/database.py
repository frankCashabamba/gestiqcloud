# app/config/database.py
from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()


def make_db_url() -> str:
    """
    Usa la URL normalizada de settings.database_url.
    Nota: si necesitas forzar SSL (cloud providers), añade `sslmode=require` en tu DATABASE_URL
    o deja esta lógica activa en prod. Ajusta a tu política.
    """
    url = settings.database_url

    # Extra safety: when running under pytest, force SQLite unless explicitly allowed.
    if os.getenv("PYTEST_CURRENT_TEST"):
        allow_pg = os.getenv("ALLOW_TEST_NON_SQLITE_DB", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if not allow_pg and not str(url).startswith("sqlite"):
            default_sqlite = Path(__file__).resolve().parents[2] / "test.db"
            url = f"sqlite:///{default_sqlite.as_posix()}"
            logger.warning(
                "[database] Forzando SQLite para tests: %s -> %s (set ALLOW_TEST_NON_SQLITE_DB=1 para permitir Postgres)",
                _mask(str(settings.database_url)),
                url,
            )

    if settings.ENVIRONMENT == "production" and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


# ---------------------------------------------------------------------------
# Engine con pooling, pre_ping y statement_timeout (vía psycopg/pg options)
# ---------------------------------------------------------------------------
STATEMENT_TIMEOUT_MS = max(1000, settings.DB_STATEMENT_TIMEOUT_MS)  # mínimo 1s

CONNECT_ARGS = {
    # Requiere driver psycopg (postgresql+psycopg://) para respetar options
    "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS}",
    "client_encoding": "UTF8",
}

_db_url = make_db_url()


def _mask(value: str | None) -> str:
    """Mask a secret value for safe logging."""
    if not value:
        return "<unset>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


logger.debug(
    "[database] PGHOST=%s PGPORT=%s PGUSER=%s DB_URL=%s",
    os.getenv("PGHOST", "<unset>"),
    os.getenv("PGPORT", "<unset>"),
    os.getenv("PGUSER", "<unset>"),
    _mask(_db_url),
)

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
# Helper: resolve legacy numeric tenant_id -> UUID
# ---------------------------------------------------------------------------
def _resolve_tenant_id(db: Session, raw_tid: str) -> str:
    """Translate a legacy numeric tenant_id to its UUID. Returns raw_tid if not numeric."""
    if not raw_tid.isdigit():
        return raw_tid
    try:
        res = db.execute(
            text("SELECT id FROM tenants WHERE tenant_id = :eid"),
            {"eid": int(raw_tid)},
        )
        row = res.first()
        if row and row[0]:
            return str(row[0])
    except Exception:
        logger.warning("Failed to resolve legacy tenant_id=%s", raw_tid, exc_info=True)
        db.rollback()
    return raw_tid


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
        dialect = getattr(getattr(db, "bind", None), "dialect", None)
        is_postgres = getattr(dialect, "name", "") == "postgresql"
        # Defensive: clear any leftover GUCs from pooled connections.
        # set_config(..., NULL, true) is transaction-local and won't error
        # even if the custom GUC was never set.
        if is_postgres:
            try:
                db.execute(text("SELECT set_config('app.tenant_id', NULL, true)"))
                db.execute(text("SELECT set_config('app.user_id', NULL, true)"))
            except Exception:
                logger.warning("Failed to clear GUCs on pooled connection", exc_info=True)
                db.rollback()

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

                # Detect superadmin: is_superadmin in claims OR scope == "admin"
                is_superadmin = bool(
                    (isinstance(claims, dict) and claims.get("is_superadmin"))
                    or (isinstance(claims, dict) and claims.get("scope") == "admin")
                )

                if tenant_id is not None and user_id is not None:
                    tid = _resolve_tenant_id(db, str(tenant_id))
                    uid = str(user_id)
                    db.execute(
                        text("SELECT set_config('app.tenant_id', :tid, true)"),
                        {"tid": tid},
                    )
                    db.execute(
                        text("SELECT set_config('app.user_id', :uid, true)"),
                        {"uid": uid},
                    )
                    db.info["tenant_id"] = tid

                # Superadmin bypass: set app.bypass_rls so admin_bypass RLS policies
                # allow operations without requiring app.tenant_id to match.
                if is_superadmin:
                    db.execute(text("SELECT set_config('app.bypass_rls', 'true', true)"))
            except Exception:
                logger.warning("Failed to set RLS GUCs for request", exc_info=True)
                db.rollback()

        # Final safeguard: ensure session isn't in aborted state before yielding
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            db.rollback()

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
_VALID_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$", re.IGNORECASE)


def set_search_path(db: Session, tenant_schema: str) -> None:
    """
    Fija el search_path por sesión (transaction-local).
    Incluye siempre 'public' como fallback.
    Llamar tras abrir la sesión (en una dependencia que resuelva el tenant).
    """
    if str(db.get_bind().url).startswith("sqlite"):
        return
    if not _VALID_SCHEMA_RE.fullmatch(tenant_schema):
        raise ValueError(f"Invalid schema name: {tenant_schema!r}")
    db.execute(
        text("SELECT set_config('search_path', :path, true)"),
        {"path": f"{tenant_schema}, public"},
    )


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
