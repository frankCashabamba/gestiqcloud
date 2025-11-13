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
import hashlib
import os
import sys
from pathlib import Path


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")


def _strip_sql_comments(sql: str) -> str:
    """Remove line (--) and block (/* */) comments and trim whitespace.

    This is a best‑effort stripper sufficient to detect truly empty files.
    It is not a full SQL parser.
    """
    import re

    # Remove block comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Remove line comments
    lines = []
    for line in sql.splitlines():
        # Drop anything after -- (not inside strings; best effort)
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    stripped = "\n".join(lines).strip()
    return stripped


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
            raise SystemExit(
                "Install psycopg (v3) or psycopg2-binary to use this script."
            ) from e


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _ensure_history_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.ops_migration_history (
          dir text PRIMARY KEY,
          checksum text NOT NULL,
          applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def _already_applied(cur, dir_name: str, checksum: str) -> tuple[bool, bool]:
    """Return (exists, same_checksum)."""
    cur.execute(
        "SELECT checksum FROM public.ops_migration_history WHERE dir = %s",
        (dir_name,),
    )
    row = cur.fetchone()
    if row is None:
        return False, False
    prev = row[0]
    return True, (prev == checksum)


def _record_applied(cur, dir_name: str, checksum: str) -> None:
    cur.execute(
        """
        INSERT INTO public.ops_migration_history(dir, checksum)
        VALUES (%s, %s)
        ON CONFLICT (dir)
        DO UPDATE SET checksum = EXCLUDED.checksum, applied_at = now()
        """,
        (dir_name, checksum),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--dsn",
        required=True,
        help="Postgres DSN, e.g., postgresql://user:pass@host/db",
    )
    p.add_argument("--dir", dest="dir", required=True, help="Migration folder path")
    p.add_argument("--action", choices=["up", "down"], default="up")
    args = p.parse_args()

    mig_dir = Path(args.dir)
    sql_file = mig_dir / ("up.sql" if args.action == "up" else "down.sql")
    sql = _read_sql(sql_file)
    if not _strip_sql_comments(sql):
        print(f"Skip empty SQL: {sql_file}")
        return 0

    conn = _connect(args.dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                # History guard: apply each migration directory at most once unless force reapply
                dir_name = mig_dir.name
                stripped = _strip_sql_comments(sql)
                checksum = _sha256(stripped)
                _ensure_history_table(cur)
                exists, same = _already_applied(cur, dir_name, checksum)
                if exists and same and args.action == "up":
                    print(f"Skip already applied: {dir_name}")
                    return 0
                if (
                    exists
                    and not same
                    and os.getenv("OPS_MIG_FORCE_REAPPLY", "0").lower()
                    not in ("1", "true", "yes")
                ):
                    print(f"Skip changed migration without force: {dir_name}")
                    return 0

                cur.execute(sql)
                if args.action == "up":
                    _record_applied(cur, dir_name, checksum)
        print(f"Applied {args.action} successfully: {sql_file}")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
