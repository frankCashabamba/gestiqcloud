#!/usr/bin/env python3
"""
Script to verify tenant_id migration for imports module.

Runs a series of checks to ensure the migration was applied correctly
and data integrity is maintained.

Usage:
    python ops/scripts/verify_tenant_migration_imports.py [--database-url URL]
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


def check_columns_exist(conn, table_name: str, columns: list) -> bool:
    """Check if specified columns exist in table."""
    for col in columns:
        result = conn.execute(
            text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = '{table_name}'
                AND column_name = '{col}'
            )
        """)
        )
        if not result.scalar():
            print(f"   ❌ Column {table_name}.{col} does not exist")
            return False
    return True


def check_no_nulls(conn, table_name: str, column_name: str) -> tuple[bool, int]:
    """Check if column has any NULL values."""
    result = conn.execute(
        text(f"""
        SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL
    """)
    )
    null_count = result.scalar()
    return null_count == 0, null_count


def check_foreign_key(conn, table_name: str, fk_name: str) -> bool:
    """Check if foreign key constraint exists."""
    result = conn.execute(
        text("""
        SELECT EXISTS (
            SELECT FROM information_schema.table_constraints 
            WHERE constraint_schema = 'public' 
            AND table_name = :table
            AND constraint_name = :fk
            AND constraint_type = 'FOREIGN KEY'
        )
    """),
        {"table": table_name, "fk": fk_name},
    )
    return result.scalar()


def check_index_exists(conn, index_name: str) -> bool:
    """Check if index exists."""
    result = conn.execute(
        text("""
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname = :idx
        )
    """),
        {"idx": index_name},
    )
    return result.scalar()


def check_jsonb_type(conn, table_name: str, column_name: str) -> bool:
    """Check if column is JSONB type."""
    result = conn.execute(
        text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = :table
        AND column_name = :col
    """),
        {"table": table_name, "col": column_name},
    )
    row = result.first()
    return row and row[0] == "jsonb"


def verify_migration(database_url: str) -> bool:
    """Run all verification checks."""
    engine = create_engine(database_url, poolclass=NullPool)

    print("=" * 70)
    print("TENANT MIGRATION VERIFICATION - IMPORTS MODULE")
    print("=" * 70)

    all_passed = True

    with engine.connect() as conn:
        # ===== CHECK 1: tenant_id columns exist =====
        print("\n[1] Checking tenant_id columns exist...")
        tables = [
            "import_batches",
            "import_items",
            "import_attachments",
            "import_mappings",
            "import_item_corrections",
            "import_lineage",
            "import_ocr_jobs",
        ]

        for table in tables:
            if check_columns_exist(conn, table, ["tenant_id"]):
                print(f"   ✅ {table}.tenant_id exists")
            else:
                all_passed = False

        # ===== CHECK 2: No NULL tenant_id values =====
        print("\n[2] Checking for NULL tenant_id values...")

        for table in tables:
            no_nulls, null_count = check_no_nulls(conn, table, "tenant_id")
            if no_nulls:
                print(f"   ✅ {table}.tenant_id has no NULLs")
            else:
                print(f"   ❌ {table}.tenant_id has {null_count} NULL values")
                all_passed = False

        # ===== CHECK 3: Foreign key constraints =====
        print("\n[3] Checking foreign key constraints...")

        fk_checks = [
            ("import_batches", "fk_import_batches_tenant"),
            ("import_items", "fk_import_items_tenant"),
            ("import_attachments", "fk_import_attachments_tenant"),
            ("import_mappings", "fk_import_mappings_tenant"),
            ("import_item_corrections", "fk_import_item_corrections_tenant"),
            ("import_lineage", "fk_import_lineage_tenant"),
            ("import_ocr_jobs", "fk_import_ocr_jobs_tenant"),
        ]

        for table, fk_name in fk_checks:
            if check_foreign_key(conn, table, fk_name):
                print(f"   ✅ {fk_name} exists")
            else:
                print(f"   ⚠️  {fk_name} not found (may use different name)")

        # ===== CHECK 4: Tenant-scoped indexes =====
        print("\n[4] Checking tenant-scoped indexes...")

        indexes = [
            "ix_import_batches_tenant_status_created",
            "ix_import_items_tenant_id",
            "ix_import_items_tenant_dedupe",
            "ix_import_attachments_tenant_id",
            "ix_import_ocr_jobs_tenant_id",
            "ix_import_ocr_jobs_tenant_status_created",
            "ix_import_mappings_tenant_source",
        ]

        for idx in indexes:
            if check_index_exists(conn, idx):
                print(f"   ✅ {idx} exists")
            else:
                print(f"   ⚠️  {idx} not found")

        # ===== CHECK 5: JSONB conversion =====
        print("\n[5] Checking JSONB type conversion...")

        jsonb_checks = [
            ("import_items", "raw"),
            ("import_items", "normalized"),
            ("import_items", "errors"),
            ("import_mappings", "mappings"),
            ("import_mappings", "transforms"),
            ("import_mappings", "defaults"),
            ("import_mappings", "dedupe_keys"),
            ("import_ocr_jobs", "result"),
        ]

        for table, column in jsonb_checks:
            if check_jsonb_type(conn, table, column):
                print(f"   ✅ {table}.{column} is JSONB")
            else:
                print(f"   ⚠️  {table}.{column} is not JSONB (may be JSON for SQLite)")

        # ===== CHECK 6: GIN indexes =====
        print("\n[6] Checking GIN indexes...")

        gin_indexes = [
            "ix_import_items_normalized_gin",
            "ix_import_items_raw_gin",
            "ix_import_mappings_mappings_gin",
        ]

        for idx in gin_indexes:
            if check_index_exists(conn, idx):
                print(f"   ✅ {idx} exists")
            else:
                print(f"   ⚠️  {idx} not found")

        # ===== CHECK 7: Unique constraint =====
        print("\n[7] Checking unique constraints...")

        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename = 'import_items'
                AND indexname = 'uq_import_items_tenant_idem'
            )
        """)
        )

        if result.scalar():
            print("   ✅ uq_import_items_tenant_idem exists")
        else:
            print("   ⚠️  uq_import_items_tenant_idem not found")

        # ===== CHECK 8: Data integrity =====
        print("\n[8] Checking data integrity...")

        # Check tenant_id consistency
        result = conn.execute(
            text("""
            SELECT COUNT(*) 
            FROM import_items i
            JOIN import_batches b ON b.id = i.batch_id
            WHERE i.tenant_id != b.tenant_id
        """)
        )

        mismatch_count = result.scalar()
        if mismatch_count == 0:
            print("   ✅ import_items.tenant_id matches batch.tenant_id")
        else:
            print(f"   ❌ Found {mismatch_count} items with mismatched tenant_id")
            all_passed = False

        # Check attachments tenant_id consistency
        result = conn.execute(
            text("""
            SELECT COUNT(*) 
            FROM import_attachments a
            JOIN import_items i ON i.id = a.item_id
            WHERE a.tenant_id != i.tenant_id
        """)
        )

        mismatch_count = result.scalar()
        if mismatch_count == 0:
            print("   ✅ import_attachments.tenant_id matches item.tenant_id")
        else:
            print(f"   ❌ Found {mismatch_count} attachments with mismatched tenant_id")
            all_passed = False

        # ===== CHECK 9: Row counts =====
        print("\n[9] Checking row counts...")

        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            print(f"   ℹ️  {table}: {count:,} rows")

        conn.commit()

    # ===== SUMMARY =====
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL CRITICAL CHECKS PASSED")
        print("\nMigration verification successful!")
        return True
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease review the issues above and fix them before proceeding.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Verify tenant_id migration for imports module"
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Database connection URL (default: from DATABASE_URL env var)",
    )

    args = parser.parse_args()

    if not args.database_url:
        print(
            "ERROR: DATABASE_URL not set. Use --database-url or set DATABASE_URL env var."
        )
        sys.exit(1)

    try:
        success = verify_migration(args.database_url)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
