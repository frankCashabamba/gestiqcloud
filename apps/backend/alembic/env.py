from __future__ import annotations

from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config, pool
from alembic import context

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Prefer DATABASE_URL env var
db_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Import target metadata from app
from app.db.base import target_metadata  # noqa: E402


def run_migrations_offline() -> None:
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

