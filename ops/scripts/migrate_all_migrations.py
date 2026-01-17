#!/usr/bin/env python3
"""
Apply all SQL migrations to local PostgreSQL database.

Usage:
    python ops/scripts/migrate_all_migrations.py [--dry-run]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


MIGRATIONS_DIR = project_root / "ops" / "migrations"


def get_migrations() -> List[Tuple[Path, str]]:
    """Get all migration directories sorted by name."""
    migrations = []

    # Skip _archive directory
    for item in sorted(MIGRATIONS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            up_sql = item / "up.sql"
            if up_sql.exists():
                migrations.append((item, up_sql.name))

    return migrations


def read_sql_file(filepath: Path) -> str:
    """Read SQL file content."""
    if not filepath.exists():
        raise FileNotFoundError(f"SQL file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def apply_migration(
    conn, migration_dir: Path, sql_content: str, dry_run: bool = False
) -> bool:
    """Apply a single migration."""
    migration_name = migration_dir.name

    if dry_run:
        print(f"\n[DRY RUN] {migration_name}")
        print("=" * 60)
        print(sql_content[:500] + "..." if len(sql_content) > 500 else sql_content)
        print("=" * 60)
        return True

    try:
        cursor = conn.cursor()
        print(f"\n> {migration_name}")

        try:
            # Execute entire SQL file as-is (PostgreSQL handles multiple statements)
            cursor.execute(sql_content)
            conn.commit()
            print("  [OK] Migration applied")
            return True

        except Exception as e:
            conn.rollback()
            print(f"  [ERROR] Error: {e}")
            return False

    except Exception as e:
        print(f"  [ERROR] Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Apply all SQL migrations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print SQL without executing"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Database connection URL (default: from DATABASE_URL env var)",
    )

    args = parser.parse_args()

    # Validate database URL
    if not args.database_url:
        print(
            "ERROR: DATABASE_URL not set. Use --database-url or set DATABASE_URL env var."
        )
        sys.exit(1)

    # Get migrations
    migrations = get_migrations()
    if not migrations:
        print("ERROR: No migrations found in ops/migrations/")
        sys.exit(1)

    print(f"Found {len(migrations)} migration(s)")
    for migration_dir, _ in migrations:
        print(f"  - {migration_dir.name}")

    # Parse database URL
    print("\nConnecting to database...")
    try:
        # postgresql://user:password@host:port/database
        from urllib.parse import urlparse

        parsed = urlparse(args.database_url)
        
        # Validate required components
        if not parsed.hostname:
            raise ValueError(
                "DATABASE_URL must include a host. "
                "Example: postgresql://user:pass@db.internal:5432/gestiqcloud"
            )
        
        if not parsed.path or parsed.path == "/":
            raise ValueError(
                "DATABASE_URL must include a database name. "
                "Example: postgresql://user:pass@host/gestiqcloud"
            )
        
        if not parsed.username:
            raise ValueError("DATABASE_URL must include a username")
        
        if not parsed.password:
            raise ValueError("DATABASE_URL must include a password")
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        print("[OK] Database connection successful")
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        sys.exit(1)

    # Apply migrations
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("DRY RUN - No changes will be made")
    else:
        print("Applying migrations...")
    print(f"{'=' * 60}")

    failed = []
    for migration_dir, _ in migrations:
        try:
            sql_content = read_sql_file(migration_dir / "up.sql")
            success = apply_migration(
                conn, migration_dir, sql_content, dry_run=args.dry_run
            )
            if not success:
                failed.append(migration_dir.name)
        except Exception as e:
            print(f"❌ Error reading migration: {e}")
            failed.append(migration_dir.name)

    conn.close()

    # Summary
    print(f"\n{'=' * 60}")
    if failed:
        print(f"[FAILED] {len(failed)} migration(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"[SUCCESS] All {len(migrations)} migration(s) applied successfully!")
        if not args.dry_run:
            print("\nNext steps:")
            print("  - Run tests: pytest app/tests/")
            print("  - Verify schema: psql -c '\\dt'")


if __name__ == "__main__":
    main()
