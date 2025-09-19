# app/test/conftest.py
import os, sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# --- Set required envs BEFORE importing any app modules ---
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("FRONTEND_URL", "http://localhost:8081")
os.environ.setdefault("TENANT_NAMESPACE_UUID", "0280249e-6707-40fb-8d60-1e8f3aea0f8e")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_SECRET_KEY", "devsecretdevsecretdevsecret")

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import (
    create_engine,
    JSON,
    text,
    event,
    Table,
    Column,
    String,
    DateTime,
    or_,
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --------- IMPORTS DE TU APP (seguros antes de app.main) ----------
from app.db.base import Base
from app.core.security import hash_password
from app.core.sessions import SessionMiddlewareServerSide

# Modelos usados por factories
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.models.auth.useradmis import SuperUser

try:
    from app.models.empresa.empresa import Empresa
except Exception:
    Empresa = None  # si no existe, lo tratamos más abajo

# JSONB opcional (para degradar a JSON en SQLite)
try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:
    JSONB = type("JSONB", (), {})  # marcador inofensivo
# ------------------------------------------------------------------


# ---------------- ENGINE/SESSION DE PRUEBAS (SQLite en memoria) ----------------
TEST_DATABASE_URL = "sqlite://"

# Evita que cualquier módulo coja una URL hacia Postgres para el resto del módulo
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # comparte la misma conexión en todos los hilos (TestClient)
)

# Foreign keys ON en SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# ------------------------------------------------------------------------------


def _ensure_auth_refresh_family(metadata):
    if "auth_refresh_family" not in metadata.tables:
        Table(
            "auth_refresh_family",
            metadata,
            Column("id", String, primary_key=True),
            Column("user_id", String, nullable=False),
            Column("tenant_id", String, nullable=False),
            Column("created_at", DateTime(timezone=True), nullable=False),
            Column("revoked_at", DateTime(timezone=True)),
        )
    if "auth_refresh_token" not in metadata.tables:
        Table(
            "auth_refresh_token",
            metadata,
            Column("id", String, primary_key=True),
            Column("family_id", String, nullable=False),
            Column("jti", String, nullable=False, unique=True),
            Column("prev_jti", String),
            Column("used_at", DateTime(timezone=True)),
            Column("revoked_at", DateTime(timezone=True)),
            Column("ua_hash", String),
            Column("ip_hash", String),
            Column("created_at", DateTime(timezone=True), nullable=False),
        )


def _demote_jsonb_and_fix_defaults(metadata):
    """Reemplaza JSONB por JSON y quita server_default con ::json (solo tests/SQLite)."""
    for table in metadata.tables.values():
        for column in table.c:
            # 1) Quitar server_default con ::json (Postgres-only)
            sd = getattr(column, "server_default", None)
            if sd is not None:
                clause = getattr(sd, "arg", None)
                txt = getattr(clause, "text", None)
                if isinstance(txt, str) and "::json" in txt:
                    column.server_default = text("'[]'")

            # 2) Degradar JSONB -> JSON
            t = column.type
            if hasattr(t, "impl") and isinstance(getattr(t, "impl", None), JSONB):
                t.impl = JSON()
            elif isinstance(t, JSONB):
                column.type = JSON()


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    _demote_jsonb_and_fix_defaults(Base.metadata)
    _ensure_auth_refresh_family(Base.metadata)
    # Asegura tablas clave de identidad (admins y usuarios de empresa)
    try:
        SuperUser.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass
    try:
        UsuarioEmpresa.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ---------- Forzar TODA la app a usar la sesión/engine de tests ----------
import app.config.database as session_mod
session_mod.engine = engine                    # parchea el engine global
session_mod.SessionLocal = TestingSessionLocal # parchea la SessionLocal


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


session_mod.get_db = _override_get_db          # parchea el provider get_db
# -------------------------------------------------------------------------


# --- IMPORTA LA APP SOLO DESPUÉS DE PARCHEAR session_mod ---
from app.main import app

# Si algún endpoint capturó Depends(get_db) en import-time:
app.dependency_overrides[session_mod.get_db] = _override_get_db


@pytest.fixture
def db():
    """Sesión de DB por test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Cliente HTTP para llamar a tus endpoints."""
    # Añadir la middleware de sesión una sola vez
    if not getattr(app.state, "has_test_session_mw", False):
        app.add_middleware(
            SessionMiddlewareServerSide,
            cookie_name="sessionid",
            secret_key="tests3cret",
            https_only=False,
        )
        app.state.has_test_session_mw = True

    # 👇 Fuerza HTTPS para que el guard de CSRF no bloquee
    with TestClient(app, base_url="https://testserver") as c:
        # Si tu app mira el proto de cabecera (reverse proxy), añade esto:
        c.headers.update({"X-Forwarded-Proto": "https"})
        yield c


# ---------------- FACTORIES ----------------
@pytest.fixture
def superuser_factory(db):
    """Crea o actualiza un superusuario (admin)."""
    def _make(*, email: str, username: str, password: str):
        existing = (
            db.query(SuperUser)
            .filter(or_(SuperUser.email == email, SuperUser.username == username))
            .first()
        )
        if existing:
            # actualizar hash si cambia y asegurar flags
            existing.password_hash = hash_password(password)
            existing.is_active = True
            existing.is_superadmin = True
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        admin = SuperUser(
            email=email,
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            is_superadmin=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    return _make


@pytest.fixture
def usuario_empresa_factory(db):
    """Crea un usuario tenant de empresa."""
    def _make(*, email: str, username: str, password: str):
        empresa_id = None
        if Empresa is not None:
            try:
                e = Empresa(nombre="Dummy SA")
                db.add(e)
                db.flush()
                empresa_id = getattr(e, "id", None)
            except Exception:
                pass

        user = UsuarioEmpresa(
            email=email,
            username=username,
            password_hash=hash_password(password),
            activo=True,
            es_admin_empresa=False,
            nombre_encargado="Nombre",
            apellido_encargado="Apellido",
            **({"empresa_id": empresa_id} if empresa_id is not None else {}),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _make
# -----------------------------------------------------------
