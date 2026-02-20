#!/usr/bin/env python3
"""
Check that public DB tables are covered by migrations (net of create/drop).

Usage:
    python ops/scripts/check_db_migrations_coverage.py [--database-url ...]
"""

import argparse
import os
import re
from pathlib import Path
from typing import Iterable, List, Set

try:
    import psycopg2
except ImportError:
    raise SystemExit("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")


PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "ops" / "migrations"

MIGRATION_OP_RE = re.compile(
    r"create\s+table\s+(if\s+not\s+exists\s+)?(?P<create>[a-zA-Z0-9_\.\"\-]+)"
    r"|drop\s+table\s+(if\s+exists\s+)?(?P<drop>[^;]+)",
    re.IGNORECASE,
)


def normalize_table_name(raw: str) -> str:
    name = raw.strip().strip('"')
    if "." in name:
        name = name.split(".")[-1].strip('"')
    # Remove trailing tokens like CASCADE/RESTRICT or parentheses.
    name = name.split()[0].split("(")[0].strip('"')
    return name


def split_drop_names(names_chunk: str) -> Iterable[str]:
    for part in names_chunk.split(","):
        token = part.strip()
        if not token:
            continue
        yield normalize_table_name(token)


def read_migration_sql() -> List[str]:
    sql_blobs = []
    for item in sorted(MIGRATIONS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith("_"):
            up_sql = item / "up.sql"
            if up_sql.exists():
                sql_blobs.append(up_sql.read_text(encoding="utf-8"))
    return sql_blobs


def expected_tables_from_migrations(sql_blobs: List[str]) -> Set[str]:
    expected: Set[str] = set()
    for sql in sql_blobs:
        for match in MIGRATION_OP_RE.finditer(sql):
            if match.group("create"):
                expected.add(normalize_table_name(match.group("create")))
                continue
            if match.group("drop"):
                for name in split_drop_names(match.group("drop")):
                    expected.discard(name)
    return expected


def fetch_db_tables(database_url: str) -> List[str]:
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )
    cur = conn.cursor()
    cur.execute(
        """
        select tablename
        from pg_catalog.pg_tables
        where schemaname = 'public'
        order by tablename
        """
    )
    rows = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check DB vs migrations coverage")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Database URL (default: DATABASE_URL env var)",
    )
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("ERROR: DATABASE_URL not set. Use --database-url or set DATABASE_URL.")

    sql_blobs = read_migration_sql()
    expected = expected_tables_from_migrations(sql_blobs)
    actual = fetch_db_tables(args.database_url)

    missing = [t for t in actual if t not in expected]
    extra = [t for t in sorted(expected) if t not in actual]

    print(f"DB tables: {len(actual)}")
    print(f"Expected tables (net migrations): {len(expected)}")
    print(f"Missing in migrations: {len(missing)}")
    for t in missing:
        print(f"  - {t}")
    print(f"Extra in migrations (not in DB): {len(extra)}")
    for t in extra:
        print(f"  - {t}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
