# backend/migrations/env.py
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Logging de Alembic (usa alembic.ini)
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Asegura imports "app.*" tanto en local como en Docker
# Este archivo vive en backend/migrations/env.py → BASE_DIR = backend/
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- (Opcional) carga .env si existe (requiere python-dotenv en requirements.txt)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# --- Importa tu Base y (opcional) settings
from app.config.database import Base  # <-- ajusta si tu Base vive en otro sitio
try:
    from app.config.settings import settings
except Exception:
    settings = None

from app.db.base import target_metadata
def running_in_docker() -> bool:
    """True si corremos dentro de un contenedor."""
    return os.path.exists("/.dockerenv") or os.getenv("DOCKERIZED") == "1"


def rewrite_db_host_if_needed(url: str) -> str:
    """
    Si estamos fuera de Docker y la URL apunta a '@db:', cámbiala a '@localhost:'.
    Así no dependemos de que la .env ponga un host distinto para local.
    """
    if not running_in_docker() and "@db:" in url:
        return url.replace("@db:", "@localhost:")
    return url


def get_db_url() -> str:
    """
    Prioridad:
      1) CLI: -x dburl=postgresql://...
      2) ENV específicas de Alembic: ALEMBIC_DBURL
      3) ENV genéricas: DATABASE_URL, LOCAL_DATABASE_URL, DOCKER_DATABASE_URL
      4) settings de la app: SQLALCHEMY_DATABASE_URI, DATABASE_URL
      5) fallback sensato según entorno (Docker vs local)
    Además: si estamos fuera de Docker y la URL trae '@db:', se reescribe a '@localhost:'.
    """
    # 1) Override por CLI
    x = context.get_x_argument(as_dictionary=True)
    if "dburl" in x and x["dburl"]:
        return rewrite_db_host_if_needed(x["dburl"])

    # 2) ENV específica para alembic (si quieres aislarla del resto de la app)
    alembic_dburl = os.getenv("ALEMBIC_DBURL")
    if alembic_dburl:
        return rewrite_db_host_if_needed(alembic_dburl)

    # 3) Variables "normales"
    for key in ("DATABASE_URL", "LOCAL_DATABASE_URL", "DOCKER_DATABASE_URL"):
        val = os.getenv(key)
        if val:
            return rewrite_db_host_if_needed(val)

    # 4) settings de la app
    for attr in ("SQLALCHEMY_DATABASE_URI", "DATABASE_URL"):
        if settings and getattr(settings, attr, None):
            return rewrite_db_host_if_needed(getattr(settings, attr))

    # 5) Fallbacks
    if running_in_docker():
        return "postgresql://postgres:root@db:5432/gestiqclouddb_dev"
    else:
        return "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"


# Inyecta la URL (deja sqlalchemy.url vacío en alembic.ini)
config.set_main_option("sqlalchemy.url", get_db_url())

# Metadata que Alembic inspecciona para autogenerate
target_metadata = Base.metadata
# Si registras modelos en un "aggregator", impórtalo aquí (sin create_all):
# import app.db.base  # noqa: F401


def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline' (sin conexión a BD)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        # include_schemas=True,  # actívalo si usas múltiples schemas
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online' (conexión a BD)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
