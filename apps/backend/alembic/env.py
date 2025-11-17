# apps/backend/alembic/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

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
# Configuración base de Alembic
# ------------------------------------------------------------
config = context.config

# Logging desde alembic.ini si existe
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefiere DATABASE_URL del entorno si está presente
db_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

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


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (sin conexión)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' (con conexión)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
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
        )

        with context.begin_transaction():
            context.run_migrations()

        # If no migrations were applied and database is empty, create schema from models
        # This handles the case where migrations directory has only placeholder migrations
        with connectable.connect() as conn:
            inspector = sa.inspect(conn)
            existing_tables = inspector.get_table_names()

            # If database is empty (no tables), create all from metadata
            if not existing_tables:
                target_metadata.create_all(connectable)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
