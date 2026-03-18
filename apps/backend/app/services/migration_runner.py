from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config.database import SessionLocal

RUNNER_RELATIVE_PATH = Path("ops") / "scripts" / "migrate_all_migrations_idempotent.py"
MIGRATIONS_RELATIVE_PATH = Path("ops") / "migrations"


def env_truthy(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def inline_migrations_allowed() -> bool:
    return env_truthy("ALLOW_INLINE_MIGRATIONS", True)


def candidate_repo_roots() -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    def push(path: Path | None) -> None:
        if path is None:
            return
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        if resolved in seen:
            return
        seen.add(resolved)
        candidates.append(resolved)

    for env_name in ("GESTIQ_REPO_ROOT", "REPO_ROOT"):
        raw = os.getenv(env_name)
        if raw:
            push(Path(raw))

    here = Path(__file__).resolve()
    for parent in here.parents:
        push(parent)

    cwd = Path.cwd()
    push(cwd)
    for parent in cwd.parents:
        push(parent)

    backend_dir = here.parents[2]
    push(backend_dir.parent.parent)
    return candidates


def find_existing_relative_path(relative_path: Path) -> Path | None:
    for root in candidate_repo_roots():
        candidate = root / relative_path
        if candidate.exists():
            return candidate
    return None


def repo_root() -> Path:
    script_path = find_existing_relative_path(RUNNER_RELATIVE_PATH)
    if script_path is not None:
        return script_path.parents[2]

    migrations_dir = find_existing_relative_path(MIGRATIONS_RELATIVE_PATH)
    if migrations_dir is not None:
        return migrations_dir.parents[1]

    backend_dir = Path(__file__).resolve().parents[2]
    return backend_dir.parent.parent


def idempotent_migrations_script() -> Path:
    override = os.getenv("GESTIQ_MIGRATION_SCRIPT") or os.getenv("INLINE_MIGRATIONS_SCRIPT")
    if override:
        return Path(override).expanduser().resolve()
    discovered = find_existing_relative_path(RUNNER_RELATIVE_PATH)
    if discovered is not None:
        return discovered
    return repo_root() / RUNNER_RELATIVE_PATH


def list_sql_migration_dirs() -> list[Path]:
    migrations_dir = repo_root() / MIGRATIONS_RELATIVE_PATH
    if not migrations_dir.exists():
        return []
    items = [
        item
        for item in migrations_dir.iterdir()
        if item.is_dir() and not item.name.startswith("_") and (item / "up.sql").exists()
    ]
    items.sort(key=lambda item: (0 if "complete_consolidated_schema" in item.name else 1, item.name))
    return items


def list_sql_migration_names() -> list[str]:
    return [item.name for item in list_sql_migration_dirs()]


def migration_friendly_name(migration_name_or_dir: str | Path) -> str:
    raw_name = (
        migration_name_or_dir.name
        if isinstance(migration_name_or_dir, Path)
        else Path(str(migration_name_or_dir)).name
    )
    parts = raw_name.split("_", 2)
    return parts[2] if len(parts) >= 3 else raw_name


def db_is_postgres(db: Session | None) -> bool:
    try:
        return bool(db and db.bind and db.bind.dialect.name == "postgresql")
    except Exception:
        return False


def qualified_table_name(db: Session | None, table_name: str) -> str:
    return f"public.{table_name}" if db_is_postgres(db) else table_name


def load_applied_sql_migration_names(db: Session | None) -> set[str]:
    if db is None or not db.bind:
        return set()
    try:
        inspector = inspect(db.bind)
        schema = "public" if db_is_postgres(db) else None
        if not inspector.has_table("_migrations", schema=schema):
            return set()
        table_name = qualified_table_name(db, "_migrations")
        rows = db.execute(sql_text(f"SELECT name FROM {table_name}")).fetchall()
        return {str(row[0]) for row in rows if row and row[0]}
    except Exception:
        return set()


def sql_migrations_status(db: Session | None = None) -> tuple[bool, int, list[str], int]:
    names = list_sql_migration_names()
    if not names:
        return (False, 0, [], 0)

    owns_session = db is None
    session = db
    if session is None:
        session = SessionLocal()

    try:
        applied = load_applied_sql_migration_names(session)
        pending = [name for name in names if name not in applied]
        applied_count = len([name for name in names if name in applied])
        return (len(pending) > 0, len(pending), pending, applied_count)
    except Exception:
        return (True, len(names), names, 0)
    finally:
        if owns_session and session is not None:
            session.close()
