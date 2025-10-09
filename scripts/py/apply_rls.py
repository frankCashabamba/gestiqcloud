#!/usr/bin/env python3
"""
Apply/repair tenant-based RLS on every table that has a `tenant_id` column.

Adds:
  - ENABLE + FORCE ROW LEVEL SECURITY
  - Single policy `rls_tenant` with USING + WITH CHECK on tenant_id
  - Ensures an index on (tenant_id)
Optional:
  - `--set-default` sets DEFAULT tenant_id := current_tenant()
  - creates helper function current_tenant() if missing

Idempotent and safe to re-run.

Usage:
  DATABASE_URL=postgres://user:pass@host:5432/db \
  python scripts/py/apply_rls.py --schema public --set-default

You can pass multiple --schema flags.
"""
from __future__ import annotations
import os
import sys
import argparse
import contextlib
import psycopg2
from psycopg2 import sql

QUERY_TABLES = sql.SQL(
    """
    SELECT c.table_schema, c.table_name
    FROM information_schema.columns c
    WHERE c.column_name = 'tenant_id'
      AND c.table_schema NOT IN ('pg_catalog','information_schema')
      {schema_filter}
    GROUP BY c.table_schema, c.table_name
    ORDER BY c.table_schema, c.table_name
    """
)

SQL_ENABLE_RLS = sql.SQL(
    """
    ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;
    """
)

SQL_DROP_POLICY = sql.SQL("DROP POLICY IF EXISTS rls_tenant ON {tbl};")

SQL_CREATE_POLICY = sql.SQL(
    """
    CREATE POLICY rls_tenant ON {tbl}
      USING (tenant_id = current_setting('app.tenant_id')::uuid)
      WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
    """
)

SQL_INDEX_EXISTS = sql.SQL(
    """
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = %s AND tablename = %s AND indexname = %s
    """
)

SQL_CREATE_INDEX = sql.SQL(
    """
    CREATE INDEX {ix} ON {tbl} (tenant_id);
    """
)

SQL_COL_DEFAULT = sql.SQL(
    """
    SELECT column_default
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s AND column_name = 'tenant_id'
    """
)

SQL_CREATE_FN_CURRENT_TENANT = """
CREATE OR REPLACE FUNCTION current_tenant() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT current_setting('app.tenant_id', true)::uuid
$$;
"""

SQL_SET_DEFAULT = sql.SQL(
    """
    ALTER TABLE {tbl}
      ALTER COLUMN tenant_id SET DEFAULT current_tenant();
    """
)


def apply_rls(conn, schemas: list[str], set_default: bool) -> None:
    with conn, conn.cursor() as cur:
        # Build schema filter
        if schemas:
            placeholders = sql.SQL(',').join(sql.Placeholder() * len(schemas))
            schema_filter = sql.SQL("AND c.table_schema IN (" + placeholders.as_string(conn) + ")")
        else:
            schema_filter = sql.SQL("")

        # Fetch tables
        cur.execute(QUERY_TABLES.format(schema_filter=schema_filter), schemas)
        tables = cur.fetchall()
        print(f"Found {len(tables)} tenant tables.")

        if set_default:
            # Ensure helper function exists
            cur.execute(SQL_CREATE_FN_CURRENT_TENANT)

        for schema, table in tables:
            tbl_ident = sql.Identifier(schema, table)
            ix_name = f"ix_{table}_tenant_id"
            ix_ident = sql.Identifier(ix_name)

            print(f"→ Applying RLS on {schema}.{table} …")

            # ENABLE + FORCE RLS
            cur.execute(SQL_ENABLE_RLS.format(tbl=tbl_ident))

            # (Re)create policy
            cur.execute(SQL_DROP_POLICY.format(tbl=tbl_ident))
            cur.execute(SQL_CREATE_POLICY.format(tbl=tbl_ident))

            # Ensure index on tenant_id
            cur.execute(SQL_INDEX_EXISTS, (schema, table, ix_name))
            if cur.fetchone() is None:
                cur.execute(SQL_CREATE_INDEX.format(ix=ix_ident, tbl=tbl_ident))
                print(f"  + Created index {ix_name}")

            # Optional: set DEFAULT tenant_id := current_tenant()
            if set_default:
                cur.execute(SQL_COL_DEFAULT, (schema, table))
                default_expr = cur.fetchone()[0]
                if not default_expr:
                    cur.execute(SQL_SET_DEFAULT.format(tbl=tbl_ident))
                    print("  + Set DEFAULT tenant_id := current_tenant()")

        print("Done. RLS policies are in place and indexed.")


def main():
    parser = argparse.ArgumentParser(description="Apply tenant RLS to all tables that contain tenant_id")
    parser.add_argument('--schema', action='append', default=[], help='Schema to include (repeatable)')
    parser.add_argument('--set-default', action='store_true', help='Set DEFAULT tenant_id := current_tenant()')
    args = parser.parse_args()

    dsn = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_DSN')
    if not dsn:
        print("ERROR: set DATABASE_URL env var.", file=sys.stderr)
        sys.exit(1)

    with contextlib.closing(psycopg2.connect(dsn)) as conn:
        apply_rls(conn, args.schema, args.set_default)


if __name__ == '__main__':
    main()
