#!/usr/bin/env python3
"""Verify RLS policies are correctly applied to imports tables.

Usage:
    python ops/scripts/verify_rls_imports.py
    python ops/scripts/verify_rls_imports.py --test-isolation

Requirements:
    - DATABASE_URL environment variable
    - PostgreSQL with RLS policies applied
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apps/backend"))

from app.models.core.modelsimport import ImportBatch

IMPORTS_TABLES = [
    "import_batches",
    "import_items",
    "import_mappings",
    "import_item_corrections",
    "import_lineage",
    "import_attachments",
    "import_ocr_jobs",
]


def get_db_session() -> Session:
    """Create database session."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def check_rls_enabled(db: Session, tables: List[str]) -> dict:
    """Verify RLS is enabled on all tables."""
    results = {}

    query = text(
        """
        SELECT
            tablename,
            CASE WHEN rowsecurity THEN 'ENABLED' ELSE 'DISABLED' END as rls_status,
            CASE WHEN rowsecurity AND NOT relforcerowsecurity THEN 'NO'
                 WHEN rowsecurity AND relforcerowsecurity THEN 'YES'
                 ELSE 'N/A' END as force_rls
        FROM pg_tables pt
        LEFT JOIN pg_class pc ON pc.relname = pt.tablename
        WHERE pt.schemaname = 'public'
          AND pt.tablename = ANY(:tables)
    """
    )

    rows = db.execute(query, {"tables": tables}).fetchall()

    for row in rows:
        results[row[0]] = {
            "rls_enabled": row[1] == "ENABLED",
            "force_rls": row[2] == "YES",
        }

    return results


def check_policies_exist(db: Session, tables: List[str]) -> dict:
    """Verify CRUD policies exist for each table."""
    results = {}

    query = text(
        """
        SELECT
            tablename,
            policyname,
            cmd
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = ANY(:tables)
        ORDER BY tablename, cmd
    """
    )

    rows = db.execute(query, {"tables": tables}).fetchall()

    for table in tables:
        table_policies = [r for r in rows if r[0] == table]

        has_select = any("SELECT" in r[2] for r in table_policies)
        has_insert = any("INSERT" in r[2] for r in table_policies)
        has_update = any("UPDATE" in r[2] for r in table_policies)
        has_delete = any("DELETE" in r[2] for r in table_policies)

        results[table] = {
            "policies": [{"name": r[1], "cmd": r[2]} for r in table_policies],
            "has_crud": has_select and has_insert and has_update and has_delete,
        }

    return results


def test_isolation(db: Session) -> dict:
    """Test RLS isolation with two tenants."""
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    results = {"success": True, "errors": []}

    try:
        # Create test data for tenant A
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_a)})
        batch_a = ImportBatch(
            tenant_id=tenant_a,
            empresa_id=999,
            source="rls_test_a",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db.add(batch_a)
        db.commit()
        batch_a_id = batch_a.id

        # Create test data for tenant B
        db.begin()
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_b)})
        batch_b = ImportBatch(
            tenant_id=tenant_b,
            empresa_id=998,
            source="rls_test_b",
            status="PENDING",
            created_at=datetime.now(timezone.utc),
        )
        db.add(batch_b)
        db.commit()
        batch_b_id = batch_b.id

        # Test 1: Tenant A should see only their batch
        db.begin()
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_a)})
        batches = (
            db.query(ImportBatch)
            .filter(ImportBatch.id.in_([batch_a_id, batch_b_id]))
            .all()
        )

        if len(batches) != 1 or batches[0].id != batch_a_id:
            results["success"] = False
            results["errors"].append(
                f"Tenant A saw {len(batches)} batches (expected 1 with id={batch_a_id})"
            )

        # Test 2: Tenant B should see only their batch
        db.commit()
        db.begin()
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_b)})
        batches = (
            db.query(ImportBatch)
            .filter(ImportBatch.id.in_([batch_a_id, batch_b_id]))
            .all()
        )

        if len(batches) != 1 or batches[0].id != batch_b_id:
            results["success"] = False
            results["errors"].append(
                f"Tenant B saw {len(batches)} batches (expected 1 with id={batch_b_id})"
            )

        # Test 3: No tenant context should see 0 rows
        db.commit()
        db.begin()
        db.execute(text("RESET app.tenant_id"))
        batches = (
            db.query(ImportBatch)
            .filter(ImportBatch.id.in_([batch_a_id, batch_b_id]))
            .all()
        )

        if len(batches) != 0:
            results["success"] = False
            results["errors"].append(
                f"No tenant context saw {len(batches)} batches (expected 0)"
            )

        # Cleanup
        db.commit()
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_a)})
        db.query(ImportBatch).filter(ImportBatch.id == batch_a_id).delete()
        db.commit()

        db.begin()
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_b)})
        db.query(ImportBatch).filter(ImportBatch.id == batch_b_id).delete()
        db.commit()

    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Exception during isolation test: {e}")
        db.rollback()

    return results


def main():
    """Run verification checks."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify RLS for imports module")
    parser.add_argument(
        "--test-isolation",
        action="store_true",
        help="Run isolation tests (creates/deletes test data)",
    )
    args = parser.parse_args()

    db = get_db_session()

    print("=" * 60)
    print("RLS Verification for Imports Module")
    print("=" * 60)

    # Check 1: RLS enabled
    print("\n1. Checking RLS is enabled...")
    rls_status = check_rls_enabled(db, IMPORTS_TABLES)
    all_enabled = True
    for table, status in rls_status.items():
        symbol = "✓" if status["rls_enabled"] and status["force_rls"] else "✗"
        force = "FORCE" if status["force_rls"] else "normal"
        print(f"  {symbol} {table}: {force}")
        if not (status["rls_enabled"] and status["force_rls"]):
            all_enabled = False

    if all_enabled:
        print("  ✓ All tables have RLS ENABLED and FORCE")
    else:
        print("  ✗ Some tables missing RLS or FORCE")

    # Check 2: CRUD policies
    print("\n2. Checking CRUD policies...")
    policies = check_policies_exist(db, IMPORTS_TABLES)
    all_have_crud = True
    for table, info in policies.items():
        symbol = "✓" if info["has_crud"] else "✗"
        policy_count = len(info["policies"])
        print(f"  {symbol} {table}: {policy_count} policies")
        if not info["has_crud"]:
            all_have_crud = False
            missing = []
            cmds = [p["cmd"] for p in info["policies"]]
            if "SELECT" not in " ".join(cmds):
                missing.append("SELECT")
            if "INSERT" not in " ".join(cmds):
                missing.append("INSERT")
            if "UPDATE" not in " ".join(cmds):
                missing.append("UPDATE")
            if "DELETE" not in " ".join(cmds):
                missing.append("DELETE")
            print(f"    Missing: {', '.join(missing)}")

    if all_have_crud:
        print("  ✓ All tables have full CRUD policies")
    else:
        print("  ✗ Some tables missing CRUD policies")

    # Check 3: Isolation test
    if args.test_isolation:
        print("\n3. Testing tenant isolation...")
        isolation_results = test_isolation(db)
        if isolation_results["success"]:
            print("  ✓ Isolation tests passed")
        else:
            print("  ✗ Isolation tests FAILED:")
            for error in isolation_results["errors"]:
                print(f"    - {error}")

    # Summary
    print("\n" + "=" * 60)
    all_passed = all_enabled and all_have_crud
    if args.test_isolation:
        all_passed = all_passed and isolation_results["success"]

    if all_passed:
        print("✓ ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
