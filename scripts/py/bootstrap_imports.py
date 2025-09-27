"""
Bootstrap script for the Imports pipeline.

Goals:
- Single entry point to run (optionally) migrations and verify schema.
- Works in any server/container calling this script once.

Behavior:
- If IMPORTS_ENABLED is falsy â†’ exit(0) immediately (nothing to check/apply).
- Else:
  - Auto-apply all migrations in ops/migrations (idempotent if SQL uses IF NOT EXISTS).
  - Verify required tables/columns/indexes for the Imports module.
  - Exit code 0 if OK, non-zero if missing.

Usage examples:
  DB_DSN=postgresql://user:pass@host/db python scripts/py/bootstrap_imports.py
  python scripts/py/bootstrap_imports.py --dsn postgresql://user:pass@host/db --dir ops/migrations
  python scripts/py/bootstrap_imports.py --dsn postgresql://.. --check-only  # only verify schema
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable, Dict, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy import inspect as sa_inspect


def _connect_psycopg(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2.connect(dsn)
        except ImportError as e:
            raise SystemExit("Install psycopg or psycopg2-binary to use bootstrap_imports") from e


def _iter_migration_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and (p / "up.sql").exists()])


def _auto_migrate(dsn: str, root_dir: Path) -> None:
    conn = _connect_psycopg(dsn)
    try:
        with conn:
            def _strip_sql_comments(s: str) -> str:
                import re
                s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
                s = "\n".join([ln.split("--", 1)[0] for ln in s.splitlines()])
                return s.strip()

            for mig in _iter_migration_dirs(root_dir):
                raw_sql = (mig / "up.sql").read_text(encoding="utf-8")
                up_sql = raw_sql.strip()
                effective = _strip_sql_comments(up_sql)
                if not effective:
                    print(f"Skip (empty up.sql): {mig.name}")
                    continue
                try:
                    with conn.cursor() as cur:
                        cur.execute(up_sql)
                    conn.commit()
                    print(f"Applied: {mig.name}")
                except Exception as e:
                    conn.rollback()
                    msg = str(e).lower()
                    if "already exists" in msg or "duplicate" in msg:
                        print(f"Skip (already applied): {mig.name}")
                        continue
                    raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


REQUIRED_TABLES: Dict[str, List[str]] = {
    "import_batches": ["id", "empresa_id", "source_type", "origin", "status"],
    "import_items": ["id", "batch_id", "idx", "raw", "status", "idempotency_key"],
    "import_mappings": ["id", "empresa_id", "name", "source_type"],
    "import_item_corrections": ["id", "empresa_id", "item_id", "user_id", "field"],
    "import_lineage": ["id", "empresa_id", "item_id", "promoted_to"],
    "auditoria_importacion": ["id", "empresa_id", "documento_id", "fecha", "batch_id", "item_id"],
}

REQUIRED_INDEXES: Dict[str, List[Tuple[str, str]]] = {
    "import_items": [
        ("unique", "idempotency_key"),
        ("index", "batch_id"),
        ("index", "dedupe_hash"),
    ]
}


def _engine(dsn: str) -> Engine:
    url = make_url(dsn)
    if url.get_backend_name() not in ("postgresql", "postgresql+psycopg2", "postgresql+psycopg"):
        raise SystemExit("This checker is intended for PostgreSQL DSNs.")
    return create_engine(dsn, future=True)


def _check_schema(dsn: str) -> Tuple[List[str], List[str]]:
    engine = _engine(dsn)
    insp = sa_inspect(engine)
    tables = set(insp.get_table_names())
    missing_tables: List[str] = []
    missing_columns: List[str] = []

    for tbl, cols in REQUIRED_TABLES.items():
        if tbl not in tables:
            missing_tables.append(tbl)
            continue
        existing_cols = {c["name"] for c in insp.get_columns(tbl)}
        for c in cols:
            if c not in existing_cols:
                missing_columns.append(f"{tbl}.{c}")

    with engine.connect() as conn:
        for tbl, rules in REQUIRED_INDEXES.items():
            for kind, col in rules:
                if kind == "unique":
                    q = text(
                        """
                        SELECT 1
                        FROM pg_indexes i
                        JOIN pg_class t ON t.relname = i.tablename
                        WHERE i.tablename = :tbl
                          AND i.indexdef ILIKE '%' || :col || '%'
                          AND i.indexdef ILIKE '%UNIQUE%'
                        LIMIT 1
                        """
                    )
                else:
                    q = text(
                        """
                        SELECT 1
                        FROM pg_indexes i
                        WHERE i.tablename = :tbl
                          AND i.indexdef ILIKE '%' || :col || '%'
                        LIMIT 1
                        """
                    )
                ok = conn.execute(q, {"tbl": tbl, "col": col}).scalar() is not None
                if not ok:
                    missing_columns.append(f"{tbl} (missing {kind} on {col})")
    return missing_tables, missing_columns


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", default=os.environ.get("DB_DSN", ""))
    p.add_argument("--dir", default=os.environ.get("MIGRATIONS_DIR", "ops/migrations"))
    p.add_argument("--check-only", action="store_true")
    args = p.parse_args()

    imports_enabled = os.environ.get("IMPORTS_ENABLED", "1").lower() in ("1", "true", "yes")
    if not imports_enabled:
        print("IMPORTS_ENABLED is false; skipping imports bootstrap")
        return 0

    if not args.dsn:
        raise SystemExit("Provide --dsn or set DB_DSN env var")

    # Apply migrations unless check-only
    if not args.check_only:
        _auto_migrate(args.dsn, Path(args.dir))

    # Verify schema
    missing_tables, missing_columns = _check_schema(args.dsn)
    if not missing_tables and not missing_columns:
        print("OK: imports schema present")
        return 0
    if missing_tables:
        print("Missing tables:")
        for t in missing_tables:
            print(" -", t)
    if missing_columns:
        print("Missing columns/indexes:")
        for c in missing_columns:
            print(" -", c)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


