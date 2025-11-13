#!/usr/bin/env python3
"""
Script to apply tenant_id migration to imports module tables.

This script applies the SQL migration from ops/migrations/2025-10-17_050_add_tenant_id_to_imports/
with safety checks and rollback support.

Usage:
    python ops/scripts/apply_tenant_migration_imports.py [--dry-run] [--database-url URL]

Options:
    --dry-run          Print SQL without executing
    --database-url     Database connection string (default: from DATABASE_URL env var)
    --rollback         Apply down.sql to rollback changes
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool
except ImportError:
    print(
        "ERROR: SQLAlchemy not installed. Run: pip install sqlalchemy psycopg2-binary"
    )
    sys.exit(1)


MIGRATION_DIR = (
    project_root / "ops" / "migrations" / "2025-10-17_050_add_tenant_id_to_imports"
)
UP_SQL = MIGRATION_DIR / "up.sql"
DOWN_SQL = MIGRATION_DIR / "down.sql"


def read_sql_file(filepath: Path) -> str:
    """Read SQL file content."""
    if not filepath.exists():
        raise FileNotFoundError(f"SQL file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def validate_prerequisites(engine):
    """Validate that prerequisites are met before migration."""
    with engine.connect() as conn:
        # Check if tenants table exists
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tenants'
            )
        """)
        )
        if not result.scalar():
            print(
                "ERROR: public.tenants table does not exist. Run tenant bootstrap migration first."
            )
            return False

        # Check if core_empresa has tenant_id
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'core_empresa'
                AND column_name = 'tenant_id'
            )
        """)
        )
        if not result.scalar():
            print("WARNING: core_empresa.tenant_id does not exist. Backfill may fail.")
            return False

        # Check if import tables exist
        tables = [
            "import_batches",
            "import_items",
            "import_mappings",
            "import_item_corrections",
            "import_lineage",
            "import_attachments",
            "import_ocr_jobs",
        ]
        for table in tables:
            result = conn.execute(
                text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                )
            """)
            )
            if not result.scalar():
                print(
                    f"WARNING: Table {table} does not exist. Migration may be incomplete."
                )

        conn.commit()

    return True


def apply_migration(engine, sql_content: str, dry_run: bool = False):
    """Apply migration SQL."""
    if dry_run:
        print("=== DRY RUN - SQL to be executed ===")
        print(sql_content)
        print("=== END DRY RUN ===")
        return True

    try:
        with engine.connect() as conn:
            # Execute as a transaction
            trans = conn.begin()
            try:
                # Split by statements (simple split by semicolon)
                statements = [s.strip() for s in sql_content.split(";") if s.strip()]

                for i, stmt in enumerate(statements, 1):
                    # Skip comments
                    if stmt.startswith("--") or not stmt:
                        continue

                    print(f"Executing statement {i}/{len(statements)}...")
                    conn.execute(text(stmt))

                trans.commit()
                print("✅ Migration applied successfully!")
                return True

            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {e}")
                print("Transaction rolled back.")
                return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Apply tenant_id migration to imports module"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print SQL without executing"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Database connection URL (default: from DATABASE_URL env var)",
    )
    parser.add_argument(
        "--rollback", action="store_true", help="Rollback migration (apply down.sql)"
    )

    args = parser.parse_args()

    # Validate database URL
    if not args.database_url:
        print(
            "ERROR: DATABASE_URL not set. Use --database-url or set DATABASE_URL env var."
        )
        sys.exit(1)

    # Create engine
    print("Connecting to database...")
    engine = create_engine(args.database_url, poolclass=NullPool)

    # Select SQL file
    sql_file = DOWN_SQL if args.rollback else UP_SQL
    action = "Rollback" if args.rollback else "Migration"

    print(f"\n{'=' * 60}")
    print(f"{action}: Add tenant_id to imports module")
    print(f"SQL File: {sql_file.name}")
    print(f"{'=' * 60}\n")

    # Read SQL
    try:
        sql_content = read_sql_file(sql_file)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Validate prerequisites (skip for rollback)
    if not args.rollback and not args.dry_run:
        print("Validating prerequisites...")
        if not validate_prerequisites(engine):
            print("\n⚠️  Prerequisites not met. Continue anyway? [y/N]: ", end="")
            response = input().strip().lower()
            if response != "y":
                print("Migration aborted.")
                sys.exit(1)

    # Apply migration
    success = apply_migration(engine, sql_content, dry_run=args.dry_run)

    if success and not args.dry_run:
        print(f"\n✅ {action} completed successfully!")
        print("\nNext steps:")
        if args.rollback:
            print("  - Review application code to ensure compatibility")
        else:
            print("  - Update application code to use tenant_id")
            print("  - Test RLS policies with: python ops/scripts/test_rls.py")
            print("  - empresa_id will be deprecated in v2.0")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
