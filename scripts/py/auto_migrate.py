"""
Auto-migration runner for ops/migrations/* folders.

Behavior:
- Scans ops/migrations/* folders in lexicographic order (timestamped).
- Executes up.sql for each folder against the provided Postgres DSN.
- Intended to be idempotent if SQL uses IF NOT EXISTS guards.

Usage:
  DB_DSN=postgresql://user:pass@host/db python scripts/py/auto_migrate.py
  python scripts/py/auto_migrate.py --dsn postgresql://user:pass@host/db

Notes:
- Safe to run at container start when guarded with env flags (e.g., RUN_MIGRATIONS=1).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


def _connect(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2.connect(dsn)
        except ImportError as e:
            raise SystemExit("Install psycopg or psycopg2-binary to use auto_migrate") from e


def _iter_migration_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and (p / "up.sql").exists()])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", default=os.environ.get("DB_DSN", ""))
    p.add_argument("--dir", default="ops/migrations", help="Root migrations dir")
    args = p.parse_args()

    if not args.dsn:
        raise SystemExit("Provide --dsn or set DB_DSN env var")

    root = Path(args.dir)
    conn = _connect(args.dsn)

    try:
        with conn:
            with conn.cursor() as cur:
                def _strip_sql_comments(s: str) -> str:
                    import re
                    # Remove /* ... */ blocks
                    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
                    # Remove -- comments per line
                    s = "\n".join([ln.split("--", 1)[0] for ln in s.splitlines()])
                    return s.strip()

                for mig in _iter_migration_dirs(root):
                    raw_sql = (mig / "up.sql").read_text(encoding="utf-8")
                    up_sql = raw_sql.strip()
                    effective = _strip_sql_comments(up_sql)
                    if not effective:
                        print(f"Skip (empty up.sql): {mig.name}")
                        continue
                    try:
                        cur.execute(up_sql)
                        print(f"Applied: {mig.name}")
                    except Exception as e:
                        # If the SQL isn't fully idempotent, log and continue or abort as needed.
                        # For safety, we continue only on 'already exists' patterns; else re-raise.
                        msg = str(e).lower()
                        if "already exists" in msg or "duplicate" in msg:
                            print(f"Skip (already applied): {mig.name}")
                            continue
                        raise
        print("Auto-migrate done")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
