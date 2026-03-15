#!/usr/bin/env python3
"""
Rollback a single migration and remove its tracking record.

Usage:
    python ops/scripts/rollback_migration.py MIGRATION_NAME [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "ops" / "migrations"


def connect(database_url: str):
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    if not parsed.hostname:
        raise ValueError("DATABASE_URL must include a host")
    if not parsed.path or parsed.path == "/":
        raise ValueError("DATABASE_URL must include a database name")
    if not parsed.username:
        raise ValueError("DATABASE_URL must include a username")
    if not parsed.password:
        raise ValueError("DATABASE_URL must include a password")
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


def is_migration_applied(conn, name: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM _migrations WHERE name = %s", (name,))
    return cur.fetchone() is not None


def remove_migration_record(conn, name: str) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM _migrations WHERE name = %s", (name,))
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Rollback a single SQL migration")
    parser.add_argument("migration", help="Migration folder name to rollback")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL without executing")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Database URL (default: DATABASE_URL env var)",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: DATABASE_URL not set.")
        sys.exit(1)

    migration_dir = MIGRATIONS_DIR / args.migration
    if not migration_dir.is_dir():
        print(f"ERROR: Migration directory not found: {migration_dir}")
        sys.exit(1)

    down_sql = migration_dir / "down.sql"
    if not down_sql.exists():
        print(f"ERROR: down.sql not found in {migration_dir}")
        sys.exit(1)

    sql_content = down_sql.read_text(encoding="utf-8")
    if not sql_content.strip():
        print(f"ERROR: down.sql is empty for {args.migration}")
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would rollback: {args.migration}")
        print("=" * 60)
        print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
        print("=" * 60)
        return

    conn = connect(args.database_url)

    if not is_migration_applied(conn, args.migration):
        print(f"[WARNING] Migration '{args.migration}' is not recorded in _migrations")
        print("Proceeding with down.sql execution anyway...")

    print(f"Rolling back: {args.migration}")
    try:
        cur = conn.cursor()
        cur.execute(sql_content)
        conn.commit()
        print("  [OK] down.sql executed")
    except Exception as e:
        conn.rollback()
        print(f"  [ERROR] Rollback failed: {e}")
        conn.close()
        sys.exit(1)

    remove_migration_record(conn, args.migration)
    print("  [OK] Removed from _migrations")
    conn.close()
    print(f"[SUCCESS] Migration '{args.migration}' rolled back")


if __name__ == "__main__":
    main()
