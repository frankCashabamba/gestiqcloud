"""Tests de la sesión DB única (C-01/C-02).

- Estructurales (siempre): `app.db.session` ya no tiene engine/SessionLocal
  propios; es un shim de `app.config.database`. Los workers usan los context
  managers canónicos.
- Comportamiento (solo Postgres): system_session activa bypass_rls;
  tenant_session_scope fija app.tenant_id. SQLite no soporta SET LOCAL /
  current_setting, así que se hace skip.
"""

from __future__ import annotations

import pytest

from app.config import database as canonical
from app.config.database import IS_SQLITE

pg_only = pytest.mark.skipif(IS_SQLITE, reason="requiere PostgreSQL (RLS/GUC)")


# --------------------------------------------------------------------------- #
# C-01: no hay engine/SessionLocal alternativos
# --------------------------------------------------------------------------- #
def test_db_session_is_shim_of_canonical():
    from app.db import session as legacy

    assert legacy.engine is canonical.engine
    assert legacy.SessionLocal is canonical.SessionLocal
    # get_db_context legacy ahora es el session_scope canónico (con GUCs)
    assert legacy.get_db_context is canonical.session_scope


def test_db_session_does_not_build_its_own_engine():
    import inspect

    from app.db import session as legacy

    src = inspect.getsource(legacy)
    assert "create_engine" not in src, "db/session.py no debe crear un engine propio"


# --------------------------------------------------------------------------- #
# C-02: los workers usan los context managers canónicos
# --------------------------------------------------------------------------- #
def test_ai_tasks_uses_canonical_scopes():
    from app.workers import ai_tasks

    assert ai_tasks.session_scope is canonical.session_scope
    assert ai_tasks.tenant_session_scope is canonical.tenant_session_scope


def test_expiry_tasks_uses_canonical_scopes():
    from app.workers import expiry_tasks

    assert expiry_tasks.session_scope is canonical.session_scope
    assert expiry_tasks.tenant_session_scope is canonical.tenant_session_scope


def test_notifications_uses_canonical_scopes():
    from app.workers import notifications

    assert notifications.tenant_session_scope is canonical.tenant_session_scope
    assert notifications.system_session is canonical.system_session


def test_no_worker_imports_get_db_context_from_legacy():
    """Ningún worker debe seguir abriendo sesiones por el shim legacy."""
    import inspect

    from app.workers import ai_tasks, expiry_tasks, notifications

    for mod in (ai_tasks, expiry_tasks, notifications):
        src = inspect.getsource(mod)
        assert "from app.db.session import" not in src, f"{mod.__name__} usa el shim legacy"


# --------------------------------------------------------------------------- #
# Comportamiento de los scopes (Postgres)
# --------------------------------------------------------------------------- #
@pg_only
def test_system_session_activates_bypass():
    from app.config.database import system_session

    with system_session() as db:
        assert db.info.get("bypass_rls") is True


@pg_only
def test_tenant_session_scope_sets_tenant():
    from app.config.database import tenant_session_scope

    tid = "00000000-0000-0000-0000-000000000002"
    with tenant_session_scope(tid) as db:
        assert db.info.get("tenant_id") == tid


@pg_only
def test_app_db_connection_is_not_superuser():
    """INVARIANTE DE SEGURIDAD: la conexión de la app NO debe ser superuser.

    Postgres ignora RLS para superusers (incluso con FORCE ROW LEVEL SECURITY),
    así que un superuser deja el aislamiento multi-tenant SIN protección de RLS.

    En CI/test la BD corre como `postgres` porque el conftest necesita superuser para
    el TRUNCATE de setup (`SET session_replication_role=replica`). Por eso aquí se hace
    SKIP cuando la conexión es superuser: no es un fallo del código, es el entorno de
    test. El invariante REAL en runtime/prod lo valida
    `ops/security/verify_rls_isolation.sql` ejecutándose como el rol `gestiq_app`
    (no-superuser).
    """
    from sqlalchemy import text

    from app.config.database import system_session

    with system_session() as db:
        is_super = db.execute(
            text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        ).scalar()
    if is_super:
        pytest.skip(
            "conexión superuser (CI/test usa postgres para el setup); el invariante real "
            "se valida con verify_rls_isolation.sql como gestiq_app (no-superuser)"
        )
    assert is_super is False


@pg_only
def test_tenant_session_scope_isolates_cross_tenant():
    """tenant_session_scope(A) no debe ver filas de otro tenant (RLS real).

    Solo es concluyente con una conexión no-superuser; si la app es superuser
    el test hace skip (el invariante anterior es el que falla y avisa).
    """
    from sqlalchemy import text

    from app.config.database import system_session, tenant_session_scope

    with system_session() as db:
        if db.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar():
            pytest.skip("conexión superuser: RLS bypassed (ver test de invariante)")
        rows = db.execute(
            text(
                "SELECT tenant_id, count(*) FROM products "
                "GROUP BY tenant_id HAVING count(*) > 0 ORDER BY 2 DESC LIMIT 2"
            )
        ).fetchall()
    if len(rows) < 2:
        pytest.skip("se necesitan 2 tenants con productos")

    (tid_a, count_a), (tid_b, _) = rows
    with tenant_session_scope(str(tid_a)) as db:
        seen = db.execute(text("SELECT count(*) FROM products")).scalar()
        leaked = db.execute(
            text("SELECT count(*) FROM products WHERE tenant_id = :t"), {"t": str(tid_b)}
        ).scalar()
    assert seen == count_a, f"ve {seen} productos, esperado {count_a} (solo de A)"
    assert leaked == 0, f"FUGA: ve {leaked} productos del tenant B"
