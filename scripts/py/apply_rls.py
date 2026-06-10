#!/usr/bin/env python3
"""
Apply Row Level Security (RLS) policies to all tenant-scoped tables.

Discovers tables with a `tenant_id` column and applies a standard
isolation policy using the `app.tenant_id` GUC.

Usage:
    python scripts/py/apply_rls.py [--dry-run] [--schema public]
"""

import argparse
import os
import sys

try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Tables excluded from RLS (global/reference data or system tables)
EXCLUDED_TABLES = frozenset({
    "_migrations",
    "tenants",
    "countries",
    "currencies",
    "languages",
    "locales",
    "timezones",
    "base_roles",
    "business_types",
    "business_categories",
    "global_action_permissions",
    "spatial_ref_sys",
    "alembic_version",
    "weekdays",
    "units_of_measure",
    "document_types",
    "expense_categories_global",
    "payment_method_templates",
    "employee_statuses",
    "contract_types",
    "deduction_types",
    "gender_types",
    "cost_driver_unit_types",
    "country_id_types",
    "country_tax_codes",
})

RLS_EXPR = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def connect(database_url: str):
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    if not parsed.hostname:
        raise ValueError("DATABASE_URL must include a host")
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


def get_tenant_tables(conn, schema: str) -> list[str]:
    """Find all tables with a tenant_id column in the given schema."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT t.tablename
        FROM pg_catalog.pg_tables t
        JOIN information_schema.columns c
            ON c.table_schema = t.schemaname AND c.table_name = t.tablename
        WHERE t.schemaname = %s AND c.column_name = 'tenant_id'
        ORDER BY t.tablename
        """,
        (schema,),
    )
    return [row[0] for row in cur.fetchall()]


def get_existing_policies(conn, schema: str) -> dict[str, list[str]]:
    """Get existing RLS policies per table."""
    cur = conn.cursor()
    cur.execute("SELECT tablename, policyname FROM pg_policies WHERE schemaname = %s", (schema,))
    result: dict[str, list[str]] = {}
    for tablename, policyname in cur.fetchall():
        result.setdefault(tablename, []).append(policyname)
    return result


def apply_rls(conn, schema: str, dry_run: bool = False):
    """Apply RLS to all tenant-scoped tables."""
    tables = get_tenant_tables(conn, schema)
    existing_policies = get_existing_policies(conn, schema)

    print(f"Found {len(tables)} table(s) with tenant_id in schema '{schema}'")

    applied = 0
    skipped_excluded = 0
    skipped_existing = 0
    enabled = 0

    cur = conn.cursor()

    for table in tables:
        if table in EXCLUDED_TABLES:
            skipped_excluded += 1
            continue

        qualified = f"{schema}.{table}" if schema != "public" else table
        policies = existing_policies.get(table, [])

        if not dry_run:
            cur.execute(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
            cur.execute(f"ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY")
        enabled += 1
        print(f"  [RLS] {table}: enabled")

        if "tenant_isolation_policy" in policies:
            skipped_existing += 1
            print(f"  [SKIP] {table}: tenant_isolation_policy already exists")
            continue

        policy_sql = (
            f"CREATE POLICY tenant_isolation_policy ON {qualified} "
            f"USING (tenant_id = {RLS_EXPR}) "
            f"WITH CHECK (tenant_id = {RLS_EXPR})"
        )

        if dry_run:
            print(f"  [DRY] {table}: would create policy")
        else:
            try:
                cur.execute(policy_sql)
                print(f"  [OK] {table}: tenant_isolation_policy created")
                applied += 1
            except psycopg2.errors.DuplicateObject:
                conn.rollback()
                print(f"  [SKIP] {table}: policy already exists (race)")
                skipped_existing += 1

    if not dry_run:
        conn.commit()

    print("\nSummary:")
    print(f"  RLS enabled: {enabled}")
    print(f"  Policies created: {applied}")
    print(f"  Already existed: {skipped_existing}")
    print(f"  Excluded tables: {skipped_excluded}")


def main():
    parser = argparse.ArgumentParser(description="Apply RLS to tenant-scoped tables")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without executing")
    parser.add_argument("--schema", action="append", dest="schemas",
                        help="Schema(s) to process (default: public)")
    parser.add_argument("--set-default", action="store_true",
                        help="Set default privileges for future tables")
    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)

    schemas = args.schemas or ["public"]
    conn = connect(database_url)

    try:
        for schema in schemas:
            apply_rls(conn, schema, dry_run=args.dry_run)

        if args.set_default and not args.dry_run:
            cur = conn.cursor()
            for schema in schemas:
                cur.execute(f"GRANT USAGE ON SCHEMA {schema} TO PUBLIC")
                cur.execute(
                    f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC"
                )
            conn.commit()
            print("\nDefault privileges set for future tables")
    finally:
        conn.close()

    print("\n[SUCCESS] RLS policies applied")


if __name__ == "__main__":
    main()
