"""
sync_models_schema.py
---------------------

Best-effort helper that inspects all SQLAlchemy models (Base.metadata) and
creates any missing tables/indices in the target Postgres database before the
SQL migrations run. This prevents `UndefinedTable` errors when new models were
added but the SQL migrations have not been backfilled yet.
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import suppress
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure every SQLAlchemy model table exists in the target DB.",
    )
    parser.add_argument(
        "--dsn",
        help="Postgres DSN. Falls back to DB_DSN or DATABASE_URL env vars.",
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Print the resolved DSN (useful for debugging).",
    )
    return parser.parse_args()


def _ensure_env_dsn(dsn: str | None) -> str:
    resolved = dsn or os.getenv("DB_DSN") or os.getenv("DATABASE_URL")
    if not resolved:
        raise SystemExit("Provide --dsn or set DB_DSN / DATABASE_URL before running sync_models_schema.py")
    os.environ.setdefault("DB_DSN", resolved)
    os.environ.setdefault("DATABASE_URL", resolved)
    # Default ENV so settings load development defaults
    os.environ.setdefault("ENV", os.getenv("ENV", "development"))
    return resolved


def _ensure_sys_path() -> None:
    """Add repo root and apps/backend to sys.path so `app` imports resolve."""
    here = Path(__file__).resolve()
    # scripts/py -> scripts -> repo
    repo_root = here.parents[2] if len(here.parents) >= 3 else here.parent
    candidates = [
        str(repo_root),
        str(repo_root / "apps"),
        str(repo_root / "apps" / "backend"),
    ]
    for path in candidates:
        if path not in sys.path:
            sys.path.append(path)


def main() -> int:
    args = _parse_args()
    dsn = _ensure_env_dsn(args.dsn)
    if args.echo:
        print(f"[sync_models_schema] Using DSN: {dsn}")

    try:
        _ensure_sys_path()
        # Import after env vars are in place so the global engine picks up the DSN.
        from sqlalchemy import text

        from app.config.database import Base, engine  # type: ignore

        # Import all models to register their tables with Base.metadata
        with suppress(Exception):
            import app.models  # type: ignore  # noqa: F401
    except Exception as exc:  # pragma: no cover - requires runtime deps
        raise SystemExit(f"[sync_models_schema] Failed to import models: {exc}") from exc

    # Ensure pgcrypto exists for gen_random_uuid() defaults
    try:
        with engine.begin() as conn:  # type: ignore[name-defined]
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    except Exception as exc:  # pragma: no cover
        print(f"[sync_models_schema] Warning: could not ensure pgcrypto extension ({exc})")

    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)  # type: ignore[name-defined]
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"[sync_models_schema] Failed to create tables: {exc}") from exc

    print(f"[sync_models_schema] Ensured {len(Base.metadata.tables)} tables are present.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
