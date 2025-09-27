"""
Lightweight migration applier for SQL directories with up.sql/down.sql.

Usage:
  python scripts/py/apply_migration.py \
      --dsn postgresql://user:pass@localhost/dbname \
      --dir ops/migrations/2025-09-22_004_imports_batch_pipeline \
      --action up

Notes:
  - Requires `psycopg` (psycopg2-binary or psycopg>=3) for Postgres connections.
  - Intentionally simple: executes the whole SQL file as-is.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def _connect(dsn: str):
    try:
        import psycopg

        conn = psycopg.connect(dsn)
        return conn
    except ImportError:
        try:
            import psycopg2  # type: ignore

            conn = psycopg2.connect(dsn)
            return conn
        except ImportError as e:
            raise SystemExit("Install psycopg (v3) or psycopg2-binary to use this script.") from e


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", required=True, help="Postgres DSN, e.g., postgresql://user:pass@host/db")
    p.add_argument("--dir", dest="dir", required=True, help="Migration folder path")
    p.add_argument("--action", choices=["up", "down"], default="up")
    args = p.parse_args()

    mig_dir = Path(args.dir)
    sql_file = mig_dir / ("up.sql" if args.action == "up" else "down.sql")
    sql = _read_sql(sql_file)

    conn = _connect(args.dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        print(f"Applied {args.action} successfully: {sql_file}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

