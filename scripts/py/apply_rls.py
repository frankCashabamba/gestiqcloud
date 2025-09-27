#!/usr/bin/env python
"""Apply standard RLS policies to tenant-aware tables.

Usage:
    python scripts/py/apply_rls.py --dsn postgresql://user:pass@host:5432/db

The script looks for tables in the public schema that expose an `empresa_id`
column and ensures that row level security is enabled for them with the
standard set of policies (`tenant_isolation_*`, `tenant_insert_*`,
`tenant_update_*`).

For join tables that do not expose `empresa_id` directly, provide the
referencing parent table and foreign-key column in the `CHILD_TABLES` map
below.

The application is expected to execute::

    SET app.tenant_id = '<empresa_id>';
    SET app.user_id   = '<usuario_id>';

This script does not attempt to handle custom ownership logic (admins only,
assigned user, etc.). Add those tables manually to the map with the required
`USING`/`WITH CHECK` clauses if they differ from the default behaviour.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Mapping, Sequence

from sqlalchemy import create_engine, text
from textwrap import dedent
from sqlalchemy.engine import Connection

# Tables without empresa_id but owned by a parent table that sí lo tiene.
# Map format: table -> (parent_table, fk_column)
CHILD_TABLES: Mapping[str, tuple[str, str]] = {
    "proveedor_contactos": ("proveedores", "proveedor_id"),
    "proveedor_direcciones": ("proveedores", "proveedor_id"),
}

def table_exists(conn: Connection, table: str) -> bool:
    query = text("SELECT to_regclass('public.' || :table) IS NOT NULL")
    return bool(conn.execute(query, {"table": table}).scalar())


@dataclass
class PolicySQL:
    enable: str
    isolation: str
    insert: str
    update: str


def build_basic_policies(table: str) -> PolicySQL:
    enable = dedent(f"""
        ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
    """).strip()
    isolation = dedent(f"""
        DROP POLICY IF EXISTS tenant_isolation_{table} ON public.{table};
        CREATE POLICY tenant_isolation_{table}
          ON public.{table}
          USING (empresa_id = current_setting('app.tenant_id')::integer);
    """).strip()
    insert = dedent(f"""
        DROP POLICY IF EXISTS tenant_insert_{table} ON public.{table};
        CREATE POLICY tenant_insert_{table}
          ON public.{table}
          FOR INSERT
          WITH CHECK (empresa_id = current_setting('app.tenant_id')::integer);
    """).strip()
    update = dedent(f"""
        DROP POLICY IF EXISTS tenant_update_{table} ON public.{table};
        CREATE POLICY tenant_update_{table}
          ON public.{table}
          FOR UPDATE
          WITH CHECK (empresa_id = current_setting('app.tenant_id')::integer);
    """).strip()
    return PolicySQL(enable, isolation, insert, update)


def build_child_policies(table: str, parent: str, fk_column: str) -> PolicySQL:
    clause = dedent(f"""
        EXISTS (
          SELECT 1
          FROM public.{parent} p
          WHERE p.id = {table}.{fk_column}
            AND p.empresa_id = current_setting('app.tenant_id')::integer
        )
    """).strip()

    enable = dedent(f"""
        ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;
    """).strip()
    isolation = dedent(f"""
        DROP POLICY IF EXISTS tenant_isolation_{table} ON public.{table};
        CREATE POLICY tenant_isolation_{table}
          ON public.{table}
          USING ({clause});
    """).strip()
    insert = dedent(f"""
        DROP POLICY IF EXISTS tenant_insert_{table} ON public.{table};
        CREATE POLICY tenant_insert_{table}
          ON public.{table}
          FOR INSERT
          WITH CHECK ({clause});
    """).strip()
    update = dedent(f"""
        DROP POLICY IF EXISTS tenant_update_{table} ON public.{table};
        CREATE POLICY tenant_update_{table}
          ON public.{table}
          FOR UPDATE
          WITH CHECK ({clause});
    """).strip()
    return PolicySQL(enable, isolation, insert, update)


def fetch_tables_with_empresa(conn: Connection) -> Sequence[str]:
    query = text(
        """
        SELECT table_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_name = 'empresa_id'
        ORDER BY table_name
        """
    )
    rows = conn.execute(query).fetchall()
    return [row[0] for row in rows]


def existing_policies(conn: Connection, table: str) -> set[str]:
    query = text(
        """
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public' AND tablename = :table
        """
    )
    return {row[0] for row in conn.execute(query, {"table": table})}


def apply_segments(conn: Connection, segments: Sequence[str]) -> None:
    for segment in segments:
        conn.execute(text(segment))


def ensure_policies(conn: Connection, table: str, policy: PolicySQL) -> None:
    existing = existing_policies(conn, table)
    expected = {
        f"tenant_isolation_{table}",
        f"tenant_insert_{table}",
        f"tenant_update_{table}",
    }
    if expected.issubset(existing):
        print(f"[RLS] OK {table}")
        return
    apply_segments(conn, [policy.enable, policy.isolation, policy.insert, policy.update])
    print(f"[RLS] Updated policies for {table}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ensure tenant RLS policies exist")
    parser.add_argument("--dsn", required=True, help="PostgreSQL DSN")
    args = parser.parse_args()

    engine = create_engine(args.dsn, future=True)
    with engine.begin() as conn:
        tables = list(fetch_tables_with_empresa(conn))
        for table in tables:
            ensure_policies(conn, table, build_basic_policies(table))

        for child, (parent, fk) in CHILD_TABLES.items():
            if not table_exists(conn, child):
                print(f'[RLS] Skip {child} (table not found)')
                continue
            ensure_policies(conn, child, build_child_policies(child, parent, fk))

    print("RLS policies applied")


if __name__ == '__main__':
    main()
