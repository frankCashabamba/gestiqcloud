# apps/backend/revision_scaffold/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, engine_from_config, pool

from alembic import context

# ------------------------------------------------------------
# Monorepo path bootstrap so the revision scaffold can import `app`
# Expected layout: <root>/apps/backend/revision_scaffold/env.py
# ------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]  # apps/backend
APPS_DIR = BACKEND_DIR.parent  # apps
ROOT = APPS_DIR.parent  # repo root

for p in (ROOT, APPS_DIR, BACKEND_DIR):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# ------------------------------------------------------------
# Load environment variables before reading DATABASE_URL.
# During normal app startup this already happens, but the revision scaffold
# runs in isolation and needs the same bootstrap.
# ------------------------------------------------------------
try:
    import app.config.env_loader  # noqa: F401  # type: ignore
except Exception:
    pass

# ------------------------------------------------------------
# Base revision-scaffold configuration
# ------------------------------------------------------------
config = context.config

# Load logging from revision_scaffold.ini when available
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer DATABASE_URL/DB_DSN from the environment when present.
# engine_from_config consumes the section dict, so update that section as well.
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
# Application target metadata
# ------------------------------------------------------------
try:
    # Standard path when `app` is importable as a package
    from app.db.base import target_metadata  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    # Explicit fallback in case the absolute import fails
    import importlib

    target_metadata = importlib.import_module("apps.backend.app.db.base").target_metadata  # type: ignore


_REVISION_VERSION_TABLE = Table(
    "alembic_version",
    MetaData(),
    # Revision IDs can exceed the historical default length.
    Column("version_num", String(128), primary_key=True),
)


def run_migrations_offline() -> None:
    """Run migrations in offline mode without a DB connection."""
    url = db_url or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        version_table_impl=_REVISION_VERSION_TABLE,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode with a DB connection."""
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
            version_table_impl=_REVISION_VERSION_TABLE,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
