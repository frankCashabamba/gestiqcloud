import importlib
import os
import uuid

import pytest
from fastapi.testclient import TestClient


# MUST run this before any other imports that might load settings
def _ensure_test_env():
    os.environ.setdefault("ENV", "development")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    os.environ.setdefault("TENANT_NAMESPACE_UUID", str(uuid.uuid4()))
    os.environ.setdefault("IMPORTS_ENABLED", "1")
    os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
    os.environ.setdefault("ENDPOINT_RATE_LIMIT_ENABLED", "0")
    os.environ.setdefault("LOGIN_RATE_LIMIT_ENABLED", "0")
    # Disable Redis for tests (use in-memory fallback)
    os.environ.setdefault("REDIS_URL", "")
    os.environ.setdefault("DISABLE_REDIS", "1")
    # Set consistent JWT secrets for tests
    # Must use the same secret for both to ensure tokens signed with one can be verified with the other
    test_secret = "test-secret-key-test-secret-key-test-secret-key-1234567890"
    os.environ.setdefault("SECRET_KEY", test_secret)
    os.environ.setdefault("JWT_SECRET_KEY", test_secret)


def _recreate_sqlite_db_if_needed():
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("sqlite") and ":memory:" not in db_url:
        prefix = "sqlite:///"
        if db_url.startswith(prefix):
            path = db_url[len(prefix) :]
            db_path = os.path.abspath(path)
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass


def _load_all_models():
    # Import only models needed by tests to avoid PG-only types on SQLite
    modules = [
        "app.models.auth.useradmis",
        "app.models.auth.refresh_family",
        "app.models.empresa.empresa",
        "app.models.empresa.usuarioempresa",
        "app.models.empresa.usuario_rolempresa",
        "app.models.empresa.rolempresas",
        "app.models.empresa.settings",
        # Tenancy model so SQLite create_all creates the tenants table used by admin flows
        "app.models.tenant",
        # Imports pipeline models (UUID/JSON fields are SQLite-friendly in tests)
        "app.models.core.modelsimport",
        "app.models.inventory.warehouse",
        # POS models
        "app.models.pos.receipt",
        "app.models.pos.register",
        "app.models.pos.doc_series",
        # Import models
        "app.models.imports",
    ]
    for m in modules:
        importlib.import_module(m)


def _prune_pg_only_tables(metadata):
    # Remove tables backed by Postgres-only types if present
    pg_only = {
        "modulos_modulo",
        "modulos_empresamodulo",
        "modulos_moduloasignado",  # Uses tenant_id UUID
        "facturas_temp",
        "facturas",
        "bank_accounts",
        "bank_transactions",
        "core_auditoria_importacion",
        "auditoria_importacion",
        "product_categories",  # Uses JSONB
        "core_rolempresa",  # Uses tenant_id UUID
    }
    # Copy keys to list to avoid runtime dict-change issues
    for name in list(metadata.tables.keys()):
        if name in pg_only:
            tbl = metadata.tables[name]
            metadata.remove(tbl)


def _register_sqlite_uuid_handlers(engine):
    """Register event listeners to convert UUID objects to strings for SQLite."""
    import sqlite3
    from uuid import UUID

    if str(engine.url).startswith("sqlite"):
        # Register UUID adapter for SQLite
        def adapt_uuid(val):
            """Adapter to convert UUID to string for SQLite."""
            return str(val)

        # Make SQLite handle UUID by converting to string
        sqlite3.register_adapter(UUID, adapt_uuid)


def _create_tables_in_order(engine, metadata):
    """Create tables with FK constraint tolerance."""
    from sqlalchemy import text

    # For PostgreSQL, temporarily disable FK checks
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("SET session_replication_role = replica"))
            conn.commit()

    try:
        tables = list(metadata.sorted_tables)
        created = set()
        max_attempts = len(tables) + 1

        for attempt in range(max_attempts):
            progress = False

            for table in tables:
                if table.name in created:
                    continue

                try:
                    table.create(bind=engine, checkfirst=True)
                    created.add(table.name)
                    progress = True
                except Exception:
                    # Tolerate all errors for now, will retry
                    continue

            if len(created) == len(tables):
                break  # Success

            if not progress:
                # No progress made, stop trying
                break

    finally:
        # Re-enable FK checks if PostgreSQL
        if engine.dialect.name == "postgresql":
            with engine.connect() as conn:
                conn.execute(text("SET session_replication_role = DEFAULT"))
                conn.commit()


_ensure_test_env()


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.config.database import Base, engine

    _recreate_sqlite_db_if_needed()
    _load_all_models()
    _prune_pg_only_tables(Base.metadata)
    _register_sqlite_uuid_handlers(engine)
    _create_tables_in_order(engine, Base.metadata)
    _ensure_sqlite_stub_tables(engine)
    _ensure_default_tenant(engine)

    # Import the app only after DB is prepared to avoid importing PG-only models
    from app.main import app

    # Ensure imports router is mounted in test env (fallbacks)
    try:
        has_imports = any(
            getattr(r, "path", "").startswith("/api/v1/imports") for r in app.router.routes
        )
    except Exception:
        has_imports = False
    if not has_imports:
        # Try canonical path
        try:
            from app.modules.imports.interface.http.tenant import router as _imports_router

            app.include_router(_imports_router, prefix="/api/v1")
            has_imports = True
        except Exception as e:
            print("WARN: include imports (app.*) failed:", repr(e))
        # Try relative apps.backend path (how tests import this package)
        if not has_imports:
            try:
                from app.modules.imports.interface.http.tenant import router as _imports_router_rel

                app.include_router(_imports_router_rel, prefix="/api/v1")
                has_imports = True
            except Exception as e2:
                print("WARN: include imports (apps.backend.*) failed:", repr(e2))
    return TestClient(app)


@pytest.fixture
def db():
    from app.config.database import Base, SessionLocal, engine

    _load_all_models()
    _prune_pg_only_tables(Base.metadata)
    _register_sqlite_uuid_handlers(engine)

    # For PostgreSQL: tables already exist from migrate_all_migrations.py
    # For SQLite: create tables from metadata
    if engine.dialect.name != "postgresql":
        Base.metadata.drop_all(bind=engine)
        # Create tables in dependency order to avoid FK violations
        _create_tables_in_order(engine, Base.metadata)
        _ensure_sqlite_stub_tables(engine)

    # Ensure at least one tenant exists (for both SQLite and PostgreSQL)
    _ensure_default_tenant(engine)
    # Sanity: ensure critical tables are present
    required = {
        "auth_user",
        "company_users",
        "company_user_roles",
        "auth_refresh_family",
        "auth_refresh_token",
    }
    missing = required.difference(Base.metadata.tables.keys())
    if missing:
        # Try direct imports of critical modules, then create_all again
        importlib.import_module("app.models.auth.useradmis")
        importlib.import_module("app.models.empresa.usuarioempresa")
        importlib.import_module("app.models.empresa.usuario_rolempresa")
        importlib.import_module("app.models.auth.refresh_family")
        Base.metadata.create_all(bind=engine)
        missing = required.difference(Base.metadata.tables.keys())
        assert not missing, f"Missing tables after create_all: {missing}"
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # For SQLite only: cleanup after test (PostgreSQL uses persistent DB from migrate_all_migrations.py)
        if engine.dialect.name != "postgresql":
            Base.metadata.drop_all(bind=engine)


@pytest.fixture
def superuser_factory(db):
    def _create(
        username: str | None = None,
        email: str | None = None,
        password: str = "admin123",
    ):
        from app.models.auth.useradmis import SuperUser
        from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher

        hasher = PasslibPasswordHasher()
        if username is None:
            username = f"admin_{uuid.uuid4().hex[:6]}"
        if email is None:
            email = f"{username}@example.com"

        # Reuse if already exists (by email or username)
        existing = (
            db.query(SuperUser)
            .filter((SuperUser.email == email) | (SuperUser.username == username))
            .first()
        )
        if existing:
            return existing
        su = SuperUser(  # noqa: F841
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
    def _create(
        empresa_nombre: str = "Acme SA",
        empresa_slug: str | None = None,
        empresa_name: str | None = None,
        username: str = "tenantuser",
        email: str = "tenant@example.com",
        password: str = "tenant123",
        es_admin_empresa: bool = True,
    ):
        if empresa_name:
            empresa_nombre = empresa_name
        import uuid as _uuid

        from sqlalchemy import or_

        from app.models.empresa.usuarioempresa import CompanyUser
        from app.models.tenant import Tenant
        from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher

        hasher = PasslibPasswordHasher()

        existing = (
            db.query(CompanyUser)
            .filter(or_(CompanyUser.email == email, CompanyUser.username == username))
            .first()
        )
        if existing:
            # Get tenant from existing user
            tenant_obj = db.get(Tenant, existing.tenant_id) if existing.tenant_id else None

            if tenant_obj:
                if empresa_nombre and tenant_obj.name != empresa_nombre:
                    tenant_obj.name = empresa_nombre
                if empresa_slug and tenant_obj.slug != empresa_slug:
                    tenant_obj.slug = empresa_slug
            else:
                # Create tenant if missing
                tenant_obj = Tenant(
                    id=_uuid.uuid4(),
                    nombre=empresa_nombre,
                    slug=empresa_slug or f"t-{_uuid.uuid4().hex[:8]}",
                )
                db.add(tenant_obj)
                db.flush()
                existing.tenant_id = tenant_obj.id

            if password:
                existing.password_hash = hasher.hash(password)
            existing.is_company_admin = es_admin_empresa
            existing.is_active = True

            db.commit()
            db.refresh(existing)
            db.refresh(tenant_obj)
            return existing, tenant_obj

        # Create new tenant (Empresa table no longer exists)
        slug = empresa_slug or f"acme-{_uuid.uuid4().hex[:8]}"
        tenant = Tenant(id=_uuid.uuid4(), nombre=empresa_nombre, slug=slug)
        db.add(tenant)
        db.flush()

        usuario = CompanyUser(
            tenant_id=tenant.id,
            first_name="Test",
            last_name="User",
            email=email,
            username=username,
            is_company_admin=es_admin_empresa,
            password_hash=hasher.hash(password),
            is_active=True,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        db.refresh(tenant)
        return usuario, tenant

    return _create


@pytest.fixture
def admin_login(client: TestClient):
    def _do():
        return "test-admin-token"

    return _do


def _ensure_sqlite_stub_tables(engine):
    # Some tests touch modulos_moduloasignado; create a minimal stub in SQLite
    from sqlalchemy import text

    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS modulos_modulo (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        description TEXT,
                        active BOOLEAN,
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
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        modulo_id TEXT,
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
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        usuario_id TEXT,
                        modulo_id TEXT,
                        fecha_asignacion TEXT,
                        ver_modulo_auto BOOLEAN
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS core_rolempresa (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT,
                        nombre TEXT,
                        descripcion TEXT,
                        permisos TEXT,
                        rol_base_id TEXT,
                        creado_por_empresa BOOLEAN
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS pos_shifts (
                        id TEXT PRIMARY KEY,
                        register_id TEXT,
                        opened_by TEXT,
                        opened_at TEXT,
                        closed_at TEXT,
                        opening_float REAL,
                        closing_total REAL,
                        status TEXT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS pos_receipt_lines (
                        id TEXT PRIMARY KEY,
                        receipt_id TEXT,
                        product_id TEXT,
                        qty REAL,
                        uom TEXT,
                        unit_price REAL,
                        tax_rate REAL,
                        discount_pct REAL,
                        line_total REAL
                    )
                    """
                )
            )
            conn.commit()


def _ensure_default_tenant(engine):
    """Ensure at least one tenant row exists for dev/test fallbacks."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.tenant import Tenant

    with Session(engine) as session:
        if session.scalar(select(Tenant.id).limit(1)):
            return
        slug = f"fixture-{uuid.uuid4().hex[:8]}"
        tenant = Tenant(name="Fixture Tenant", slug=slug)
        session.add(tenant)
        session.commit()


@pytest.fixture
def tenant_with_data(db):
    """Create a tenant with sample data (products, warehouse) for testing."""
    from sqlalchemy import text

    from app.models.tenant import Tenant
    from app.models.inventory.warehouse import Warehouse

    tid = uuid.uuid4()

    # Create tenant
    tenant = Tenant(
        id=tid,
        name="Test Tenant with Data",
        slug=f"test-{tid.hex[:8]}",
    )
    db.add(tenant)
    db.flush()

    # Create warehouse
    warehouse = Warehouse(
        id=1,
        tenant_id=tid,
        name="Test Warehouse",
        code="WH001",
    )
    db.add(warehouse)
    db.flush()

    # Create sample product if using PostgreSQL
    product_id = uuid.uuid4()
    if db.get_bind().dialect.name == "postgresql":
        try:
            db.execute(
                text(
                    "INSERT INTO products (id, tenant_id, name, sku) "
                    "VALUES (:id, :tid, :name, :sku) ON CONFLICT DO NOTHING"
                ),
                {"id": product_id, "tid": tid, "name": "Test Product", "sku": "TEST-001"},
            )
        except Exception:
            pass

    db.commit()

    return {
        "tenant": tenant,
        "tenant_id": tid,
        "warehouse": warehouse,
        "product_id": product_id,
    }


@pytest.fixture
def tenant_minimal(db):
    """Create minimal tenant for smoke tests."""
    from app.models.tenant import Tenant
    from sqlalchemy import text

    tid = uuid.uuid4()
    tenant = Tenant(
        id=tid,
        name="Smoke Test Tenant",
        slug=f"smoke-{tid.hex[:8]}",
    )
    db.add(tenant)
    db.commit()

    # Disable RLS for smoke tests (tests use INSERT directly, not ORM)
    if db.get_bind().dialect.name == "postgresql":
        try:
            db.execute(text("ALTER TABLE warehouses DISABLE ROW LEVEL SECURITY"))
            db.execute(text("ALTER TABLE stock_moves DISABLE ROW LEVEL SECURITY"))
            db.execute(text("ALTER TABLE products DISABLE ROW LEVEL SECURITY"))
            db.execute(text("ALTER TABLE pos_items DISABLE ROW LEVEL SECURITY"))
            db.commit()
        except Exception:
            pass

    return {
        "tenant_id": tid,
        "tenant_id_str": str(tid),
    }
