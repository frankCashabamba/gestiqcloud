# apps/backend/alembic/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, engine_from_config, pool

from alembic import context

# ------------------------------------------------------------
# Bootstrap de paths (monorepo) para que Alembic encuentre `app`
# Estructura asumida: <root>/apps/backend/alembic/env.py
# ------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]  # apps/backend
APPS_DIR = BACKEND_DIR.parent  # apps
ROOT = APPS_DIR.parent  # repo root

for p in (ROOT, APPS_DIR, BACKEND_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# ------------------------------------------------------------
# Cargar variables de entorno (.env.local/.env) antes de leer DATABASE_URL.
# En runtime (uvicorn) esto ya ocurre al importar la app, pero Alembic se
# ejecuta de forma aislada y necesita este bootstrap.
# ------------------------------------------------------------
try:
    import app.config.env_loader  # noqa: F401  # type: ignore
except Exception:
    pass

# ------------------------------------------------------------
# Configuración base de Alembic
# ------------------------------------------------------------
config = context.config

# Logging desde alembic.ini si existe
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefiere DATABASE_URL/DB_DSN del entorno si está presente.
# Nota: engine_from_config consume el dict de sección, así que actualizamos también la sección.
db_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("DB_DSN")
    or os.getenv("SQLALCHEMY_DATABASE_URI")
    or config.get_main_option("sqlalchemy.url")
)
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)
    try:
        config.set_section_option(config.config_ini_section, "sqlalchemy.url", db_url)
    except Exception:
        pass

# ------------------------------------------------------------
# Target metadata del modelo de la app
# ------------------------------------------------------------
try:
    # Ruta "normal" cuando `app` es paquete (apps/backend/app)
    from app.db.base import target_metadata  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    # Fallback explícito por si el import absoluto falla
    import importlib

    target_metadata = importlib.import_module("apps.backend.app.db.base").target_metadata  # type: ignore


_ALEMBIC_VERSION_TABLE = Table(
    "alembic_version",
    MetaData(),
    # Our revision IDs are descriptive and can exceed 32 chars (Alembic default).
    Column("version_num", String(128), primary_key=True),
)


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (sin conexión)."""
    url = db_url or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        version_table_impl=_ALEMBIC_VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' (con conexión)."""
    section = config.get_section(config.config_ini_section) or {}
    if db_url:
        section["sqlalchemy.url"] = db_url
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            version_table_impl=_ALEMBIC_VERSION_TABLE,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
