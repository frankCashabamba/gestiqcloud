# app/config/database.py
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, text
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
def get_db() -> Iterator[Session]:
    """
    Uso:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
