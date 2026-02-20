#!/usr/bin/env python3
"""Apply minimal schema fix for tests: products.tax_rate default + not null."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import psycopg2


SQL = """
ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate SET DEFAULT 0;

UPDATE products
SET tax_rate = 0
WHERE tax_rate IS NULL;

ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate SET NOT NULL;
"""


def _resolve_db_url() -> str:
    return (
        os.getenv("TEST_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or ""
    ).strip()


def _connect(db_url: str):
    parsed = urlparse(db_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("This script only supports PostgreSQL URLs.")
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=(parsed.path or "/").lstrip("/"),
        user=parsed.username,
        password=parsed.password,
    )


def main() -> int:
    db_url = _resolve_db_url()
    if not db_url:
        print("Missing TEST_DATABASE_URL/DATABASE_URL")
        return 1

    conn = _connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
        print("[OK] products.tax_rate schema ensured")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"[ERROR] {exc}")
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
