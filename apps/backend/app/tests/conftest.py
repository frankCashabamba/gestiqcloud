# conftest.py
import os
import uuid
import importlib
import pytest

# --- MUY IMPORTANTE: fija ENV ANTES de cualquier import de la app ---
def _ensure_test_env():
    """
    Variables de entorno para tests.
    Forzamos ENV a 'development' porque tu Settings solo acepta
    'development' o 'production'.
    """
    # Fuerza siempre a 'development' para evitar ValidationError
    os.environ["ENV"] = "development"
    os.environ["RATE_LIMIT_ENABLED"] = "0"

    # El resto son valores útiles para la app en tests
    os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
    # No dependemos de esta URL porque reemplazamos el engine abajo,
    # pero la dejamos para evitar efectos colaterales
    os.environ.setdefault("DATABASE_URL", "sqlite://")
    os.environ.setdefault("TENANT_NAMESPACE_UUID", str(uuid.uuid4()))
    os.environ.setdefault("IMPORTS_ENABLED", "1")

_ensure_test_env()

from fastapi.testclient import TestClient

# --- SQLAlchemy test engine (in-memory compartida) ---
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_ENGINE = create_engine(
    "sqlite://",  # "sqlite://" (no :memory:) con StaticPool para compartir
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _load_all_models():
    """
    Importa modelos necesarios para que estén en Base.metadata.
    Añade aquí módulos reales de tu proyecto (los que existan).
    """
    modules = [
        # Auth / Identity
        "app.models.auth.useradmis",
        # Si existen nombres reales de modelo de refresh token, impórtalos:
        "app.models.auth.refreshtoken",
        "app.models.auth.refresh_token",

        # Empresa / Tenant
        "app.models.empresa.empresa",
        "app.models.empresa.usuarioempresa",
        "app.models.empresa.usuario_rolempresa",
        "app.models.empresa.rolempresas",
        "app.models.empresa.settings",
        "app.models.tenant",

        # Core / Imports
        "app.models.core.modelsimport",
        "app.models.core.idioma",
        "app.models.core.tipoempresa",
    ]
    for m in modules:
        try:
            importlib.import_module(m)
        except Exception as e:
            print(f"WARN: Could not import {m}: {e}")


def _prune_pg_only_tables(metadata):
    """
    Elimina de metadata tablas que usan tipos PostgreSQL (JSONB, HSTORE, ARRAY, etc.)
    que no compilan en SQLite. Luego creamos stubs manuales.
    """
    pg_only = {
        # --- vuelve a incluir estas tres ---
        "modulos_modulo",
        "modulos_empresamodulo",
        "modulos_moduloasignado",

        # el resto que ya tenías o quieras excluir
        "facturas_temp",
        "facturas",
        "bank_accounts",
        "bank_transactions",
        "core_auditoria_importacion",
        "auditoria_importacion",
        "sales_orders",
        "sales_order_items",
        "pos_items",
        "stock_items",
        "stock_moves",
        
        # POS tables (use stubs instead)
        "pos_registers",
        "pos_shifts",
        "pos_receipts",
        "pos_receipt_lines",
        "pos_payments",
        "doc_series",
        "store_credits",
        
        # E-invoicing tables (use stubs instead)
        "einv_credentials",
        "sri_submissions",
    }
    for name in list(metadata.tables.keys()):
        if name in pg_only:
            tbl = metadata.tables[name]
            metadata.remove(tbl)


def _ensure_sqlite_stub_tables(engine):
    """
    Crea tablas mínimas en SQLite si no existen modelos reales.
    Útil para endpoints que esperan estas tablas.
    """
    if not str(engine.url).startswith("sqlite"):
        return

    with engine.connect() as conn:
        # --- Modulos (mínimo) ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS modulos_modulo (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT,
                    descripcion TEXT,
                    activo BOOLEAN,
                    icono TEXT,
                    url TEXT,
                    plantilla_inicial TEXT,
                    context_type TEXT,
                    modelo_objetivo TEXT,
                    filtros_contexto TEXT,
                    categoria TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS modulos_empresamodulo (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,
                    modulo_id INTEGER,
                    tenant_id TEXT,
                    activo BOOLEAN,
                    fecha_activacion TEXT,
                    fecha_expiracion TEXT,
                    plantilla_inicial TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS modulos_moduloasignado (
                    id INTEGER PRIMARY KEY,
                    empresa_id INTEGER,
                    usuario_id INTEGER,
                    modulo_id INTEGER,
                    fecha_asignacion TEXT,
                    ver_modulo_auto BOOLEAN
                )
                """
            )
        )

        # --- Tenants (UUID como TEXT en SQLite) ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    empresa_id INTEGER UNIQUE NOT NULL,
                    slug TEXT UNIQUE,
                    base_currency TEXT,
                    country_code TEXT,
                    created_at TEXT
                )
                """
            )
        )

        # --- Core catálogos mínimos ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS core_idioma (
                    id INTEGER PRIMARY KEY,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS core_tipoempresa (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    descripcion TEXT
                )
                """
            )
        )

        # --- Refresh tokens (si no existe modelo real importado) ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS auth_refresh_token (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    token TEXT,
                    family TEXT,
                    revoked BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    expires_at TEXT
                )
                """
            )
        )

        # --- POS tables (stub for SQLite - without JSONB/UUID postgres types) ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pos_registers (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    default_warehouse_id INTEGER,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (tenant_id, code)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pos_shifts (
                    id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    register_id INTEGER NOT NULL REFERENCES pos_registers(id) ON DELETE CASCADE,
                    opened_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    closed_at TEXT,
                    opening_float REAL DEFAULT 0,
                    closing_total REAL,
                    status TEXT DEFAULT 'open',
                    user_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pos_receipts (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    shift_id INTEGER NOT NULL REFERENCES pos_shifts(id) ON DELETE CASCADE,
                    number TEXT,
                    status TEXT DEFAULT 'draft',
                    gross_total REAL DEFAULT 0,
                    tax_total REAL DEFAULT 0,
                    currency TEXT DEFAULT 'EUR',
                    customer_id TEXT,
                    invoice_id TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pos_receipt_lines (
                    id TEXT PRIMARY KEY,
                    receipt_id TEXT NOT NULL REFERENCES pos_receipts(id) ON DELETE CASCADE,
                    product_id TEXT NOT NULL,
                    qty REAL NOT NULL,
                    unit_price REAL NOT NULL,
                    tax_rate REAL DEFAULT 0,
                    discount_pct REAL DEFAULT 0,
                    line_total REAL NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pos_payments (
                    id TEXT PRIMARY KEY,
                    receipt_id TEXT NOT NULL REFERENCES pos_receipts(id) ON DELETE CASCADE,
                    method TEXT NOT NULL,
                    amount REAL NOT NULL,
                    ref TEXT,
                    paid_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS doc_series (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    register_id TEXT REFERENCES pos_registers(id),
                    doc_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    current_no INTEGER DEFAULT 0,
                    reset_policy TEXT DEFAULT 'yearly',
                    active BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, register_id, doc_type, name)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS store_credits (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    customer_id TEXT,
                    currency TEXT NOT NULL,
                    amount_initial REAL NOT NULL,
                    amount_remaining REAL NOT NULL,
                    expires_at TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # --- E-invoicing tables (stub for SQLite) ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS einv_credentials (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    country TEXT NOT NULL,
                    sandbox BOOLEAN DEFAULT 1,
                    cert_path TEXT,
                    has_certificate BOOLEAN DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, country)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sri_submissions (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    invoice_id TEXT,
                    status TEXT DEFAULT 'pending',
                    clave_acceso TEXT,
                    xml_content TEXT,
                    error_message TEXT,
                    submitted_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # --- SPEC-1 Tables ---
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS daily_inventory (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    stock_inicial REAL DEFAULT 0,
                    venta_unidades REAL DEFAULT 0,
                    stock_final REAL DEFAULT 0,
                    ajuste REAL DEFAULT 0,
                    precio_unitario_venta REAL,
                    importe_total REAL,
                    source_file TEXT,
                    source_row INTEGER,
                    import_digest BLOB,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                )
                """
            )
        )
        
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS purchase (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    supplier_name TEXT,
                    product_id TEXT,
                    cantidad REAL NOT NULL,
                    costo_unitario REAL NOT NULL,
                    total REAL,
                    notas TEXT,
                    source_file TEXT,
                    source_row INTEGER,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                )
                """
            )
        )
        
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS milk_record (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    litros REAL NOT NULL,
                    grasa_pct REAL,
                    notas TEXT,
                    source_file TEXT,
                    source_row INTEGER,
                    created_at TEXT NOT NULL,
                    created_by TEXT
                )
                """
            )
        )

        conn.commit()


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(scope="function")
def db():
    """
    Session de BD por test.
    - Sustituye el engine/SessionLocal de la app por el TEST_ENGINE (StaticPool).
    - Importa modelos, crea el esquema y stubs necesarios.
    """
    from app.config import database as dbm  # debe exponer engine, SessionLocal, Base

    # Importa todos los modelos para poblar Base.metadata
    _load_all_models()

    # Reemplaza engine/SessionLocal de la app por el de test
    try:
        dbm.engine.dispose()
    except Exception:
        pass

    dbm.engine = TEST_ENGINE
    dbm.SessionLocal = TestingSessionLocal
    Base = dbm.Base

    # Si hay tablas PG-only que molestan en SQLite, elimínalas de metadata
    _prune_pg_only_tables(Base.metadata)

    # Crea esquema limpio en el TEST_ENGINE
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)

    # Asegura tablas stub si no hay modelos reales
    _ensure_sqlite_stub_tables(TEST_ENGINE)

    # Sanity: si algunas requeridas no están en metadata, re-importa modelos clave
    required = {"auth_user", "core_empresa", "usuarios_usuarioempresa"}
    missing = required.difference(Base.metadata.tables.keys())
    if missing:
        for m in [
            "app.models.auth.useradmis",
            "app.models.empresa.empresa",
            "app.models.empresa.usuarioempresa",
        ]:
            try:
                importlib.import_module(m)
            except Exception as e:
                print(f"WARN: re-import {m} failed: {e}")
        Base.metadata.create_all(bind=TEST_ENGINE)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """
    TestClient por test (context manager) y Session POR REQUEST.
    Evita 'detached connection fairy' y estados cruzados.
    """
    from app.main import app
    from app.config.database import get_db

    def override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    # Monta router de imports si no está
    try:
        has_imports = any(
            getattr(r, "path", "").startswith("/api/v1/imports") for r in app.router.routes
        )
    except Exception:
        has_imports = False

    if not has_imports:
        try:
            from app.modules.imports.interface.http.tenant import router as _imports_router
            app.include_router(_imports_router, prefix="/api/v1")
        except Exception as e:
            print(f"WARN: include imports router failed: {e}")

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# Factories
# ----------------------------------------------------------------------
@pytest.fixture
def superuser_factory(db):
    """Creador de superusuarios únicos por test."""
    def _create(username: str | None = None, email: str | None = None, password: str = "admin123"):
        from app.models.auth.useradmis import SuperUser
        from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher

        hasher = PasslibPasswordHasher()

        suf = uuid.uuid4().hex[:8]
        if username is None:
            username = f"admin_{suf}"
        if email is None:
            email = f"admin_{suf}@example.com"

        existing = (
            db.query(SuperUser)
            .filter((SuperUser.email == email) | (SuperUser.username == username))
            .first()
        )
        if existing:
            return existing

        su = SuperUser(
            username=username,
            email=email,
            password_hash=hasher.hash(password),
            is_superadmin=True,
            is_staff=True,
            is_active=True,
        )
        db.add(su)
        db.commit()
        db.refresh(su)
        return su

    return _create


@pytest.fixture
def usuario_empresa_factory(db):
    """Crea un usuario de empresa + tenant UUID válido."""
    created_users = {}

    def _create(
        empresa_nombre: str = "Acme SA",
        empresa_slug: str | None = None,
        username: str = "tenantuser",
        email: str = "tenant@example.com",
        password: str = "tenant123",
        es_admin_empresa: bool = True,
    ):
        from sqlalchemy import or_
        from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
        from app.models.empresa.empresa import Empresa
        from app.models.empresa.usuarioempresa import UsuarioEmpresa
        from app.models.tenant import Tenant

        hasher = PasslibPasswordHasher()
        cache_key = f"{email}:{username}"
        if cache_key in created_users:
            return created_users[cache_key]

        existing = (
            db.query(UsuarioEmpresa)
            .filter(or_(UsuarioEmpresa.email == email, UsuarioEmpresa.username == username))
            .first()
        )
        if existing:
            empresa = existing.empresa or db.get(Empresa, existing.empresa_id)
            if password:
                existing.password_hash = hasher.hash(password)
            existing.es_admin_empresa = es_admin_empresa
            existing.activo = True
            if not existing.tenant_id:
                existing.tenant_id = uuid.uuid4()
            db.commit()
            db.refresh(existing)
            if empresa:
                db.refresh(empresa)
            created_users[cache_key] = (existing, empresa)
            return existing, empresa

        suf = uuid.uuid4().hex[:8]
        slug = empresa_slug or f"acme-{suf}"
        empresa = Empresa(nombre=empresa_nombre, slug=slug)
        db.add(empresa)
        db.flush()

        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            empresa_id=empresa.id,
            slug=f"{slug}-tenant",
            country_code="ES",
            base_currency="EUR",
        )
        db.add(tenant)
        db.flush()

        usuario = UsuarioEmpresa(
            empresa_id=empresa.id,
            tenant_id=tenant_id,
            nombre_encargado="Test",
            apellido_encargado="User",
            email=email,
            username=username,
            es_admin_empresa=es_admin_empresa,
            password_hash=hasher.hash(password),
            activo=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        db.refresh(empresa)

        created_users[cache_key] = (usuario, empresa)
        return usuario, empresa

    return _create


@pytest.fixture
def admin_login(client: TestClient):
    """Mock sencillo de login admin para tests que solo necesitan un token."""
    def _do():
        return "test-admin-token"
    return _do


@pytest.fixture
def jwt_token_factory():
    """Factory para generar tokens JWT válidos para tests."""
    from app.modules.identity.infrastructure.jwt_service import JwtService
    
    def _create(
        user_id: int = 1,
        tenant_id: str | None = None,
        empresa_id: int | None = None,
        username: str = "testuser",
        email: str = "test@example.com",
        kind: str = "access",
        **extra_claims
    ):
        service = JwtService()
        payload = {
            "sub": str(user_id),
            "user_id": user_id,  # REQUIRED: get_current_user() expects this
            "username": username,
            "email": email,
            **extra_claims
        }
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if empresa_id:
            payload["empresa_id"] = empresa_id
            
        return service.encode(payload, kind=kind)
    
    return _create


@pytest.fixture
def auth_headers(jwt_token_factory, db):
    """Headers de autenticación con token JWT válido."""
    def _create(tenant_id: str | None = None, **token_kwargs):
        from uuid import uuid4
        
        if not tenant_id:
            tenant_id = str(uuid4())
        
        # Asegurar que el tenant existe en DB (para tests)
        # SQLite compatible: INSERT OR IGNORE
        try:
            # Crear empresa si no existe (required by tenants FK)
            db.execute(
                text("""
                    INSERT OR IGNORE INTO core_empresa (id, nombre, slug)
                    VALUES (1, 'Test Empresa', 'test-empresa')
                """)
            )
            # Crear tenant
            db.execute(
                text("""
                    INSERT OR IGNORE INTO tenants (id, empresa_id, slug, country_code, base_currency)
                    VALUES (:id, 1, :slug, 'ES', 'EUR')
                """),
                {"id": tenant_id, "slug": f"test-{tenant_id[:8]}"}
            )
            db.commit()
        except Exception as e:
            # Si falla, log para debugging
            import logging
            logging.warning(f"Could not create tenant in test: {e}")
            pass
        
        token = jwt_token_factory(tenant_id=tenant_id, **token_kwargs)
        headers = {"Authorization": f"Bearer {token}"}
        headers["X-Tenant-ID"] = tenant_id
        return headers
    
    return _create
