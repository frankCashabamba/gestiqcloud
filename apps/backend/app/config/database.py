# app/config/database.py
from __future__ import annotations

import logging
import os
import re
from collections.abc import Generator, Iterator
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
    # lc_messages=C fuerza mensajes del servidor en ASCII (evita UnicodeDecodeError en Windows)
    "options": f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c lc_messages=C",
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
# RLS context extraction + GUC helpers
# ---------------------------------------------------------------------------
def _extract_rls_context(request: Request) -> dict:
    claims = getattr(request.state, "access_claims", None) or {}
    sess = getattr(request.state, "session", {}) or {}

    tenant_id = claims.get("tenant_id") if isinstance(claims, dict) else None
    user_id = claims.get("user_id") if isinstance(claims, dict) else None

    if tenant_id is None and isinstance(sess, dict):
        tenant_id = sess.get("tenant_id")
    if user_id is None and isinstance(sess, dict):
        user_id = sess.get("tenant_user_id") or sess.get("user_id")

    is_superadmin = False
    if isinstance(claims, dict):
        is_superadmin = bool(
            claims.get("is_superadmin")
            or claims.get("scope") == "admin"
            or claims.get("kind") == "admin"  # JWT admin emitido con kind="admin"
        )
    if not is_superadmin and isinstance(sess, dict):
        is_superadmin = bool(
            sess.get("is_superadmin") or sess.get("scope") == "admin" or sess.get("kind") == "admin"
        )

    return {
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "user_id": str(user_id) if user_id is not None else None,
        "bypass_rls": is_superadmin,
    }


def _apply_rls_gucs(
    connection, *, tenant_id: str | None, user_id: str | None, bypass_rls: bool
) -> None:
    """Aplica los GUCs de RLS como transaction-local en la conexión dada."""
    connection.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": tenant_id or ""},
    )
    connection.execute(
        text("SELECT set_config('app.user_id', :uid, true)"),
        {"uid": user_id or ""},
    )
    connection.execute(
        text("SELECT set_config('app.bypass_rls', :bypass, true)"),
        {"bypass": "true" if bypass_rls else "false"},
    )


# ---------------------------------------------------------------------------
# Hook after_begin: re-aplica GUCs al inicio de CADA transacción nueva,
# incluidas las que arrancan tras un db.rollback(). Esto garantiza que
# bypass_rls nunca se pierde independientemente de cuántos rollbacks ocurran.
# ---------------------------------------------------------------------------
@event.listens_for(SessionLocal, "after_begin")
def _session_after_begin(session: Session, transaction, connection):
    if connection.dialect.name != "postgresql":
        return
    _apply_rls_gucs(
        connection,
        tenant_id=session.info.get("tenant_id"),
        user_id=session.info.get("user_id"),
        bypass_rls=bool(session.info.get("bypass_rls", False)),
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

        if is_postgres:
            ctx = _extract_rls_context(request)

            # Resuelve tenant legacy numérico -> UUID antes de guardar en db.info
            if ctx["tenant_id"] is not None:
                try:
                    ctx["tenant_id"] = _resolve_tenant_id(db, ctx["tenant_id"])
                except Exception:
                    pass

            # Guarda contexto en db.info: after_begin lo reaplica en cada
            # nueva transacción (incluyendo tras cualquier db.rollback()).
            db.info["tenant_id"] = ctx["tenant_id"]
            db.info["user_id"] = ctx["user_id"]
            db.info["bypass_rls"] = bool(ctx["bypass_rls"])

            # Fuerza arranque de transacción para que after_begin aplique los GUCs ya.
            db.execute(text("SELECT 1"))

        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ORM hook: auto-fill tenant_id cuando falta (best-effort)
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


# ---------------------------------------------------------------------------
# Helpers RLS: fijar contexto y bypass temporal
# ---------------------------------------------------------------------------
def _is_postgres(db: Session) -> bool:
    return (
        getattr(getattr(db, "bind", None), "dialect", None)
        and getattr(db.bind.dialect, "name", "") == "postgresql"
    )  # type: ignore[union-attr]


def set_rls_tenant(db: Session, tenant_id: str | None) -> None:
    """Fija tenant_id en db.info y en el GUC de la transacción actual (no-op en SQLite)."""
    db.info["tenant_id"] = tenant_id
    if _is_postgres(db):
        db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id or ""},
        )


def set_rls_user(db: Session, user_id: str | None) -> None:
    """Fija user_id en db.info y en el GUC de la transacción actual (no-op en SQLite)."""
    db.info["user_id"] = user_id
    if _is_postgres(db):
        db.execute(
            text("SELECT set_config('app.user_id', :uid, true)"),
            {"uid": user_id or ""},
        )


@contextmanager
def temp_rls_bypass(db: Session) -> Generator[None, None, None]:
    """
    Context manager que activa bypass_rls temporalmente y lo restaura al salir.
    No-op en SQLite (los tests no tienen RLS).

    Uso:
        with temp_rls_bypass(db):
            user = db.query(User).filter(...).first()
    """
    if not _is_postgres(db):
        yield
        return

    prev = bool(db.info.get("bypass_rls", False))
    db.info["bypass_rls"] = True
    db.execute(text("SELECT set_config('app.bypass_rls', 'true', true)"))
    try:
        yield
    finally:
        db.info["bypass_rls"] = prev
        db.execute(
            text("SELECT set_config('app.bypass_rls', :v, true)"),
            {"v": "true" if prev else "false"},
        )


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


# ---------------------------------------------------------------------------
# Auditoría automática: registra en audit_events cada create/update/delete
# Se activa al importar database.py (siempre que no sea SQLite de tests)
# ---------------------------------------------------------------------------
try:
    from app.core.auto_audit import register_auto_audit  # noqa: E402

    register_auto_audit(SessionLocal)
    logger.debug("[database] Auto-auditoría ORM registrada sobre SessionLocal")
except Exception as _auto_audit_exc:
    logger.warning("[database] No se pudo registrar auto_audit: %s", _auto_audit_exc)
