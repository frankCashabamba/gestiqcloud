#!/usr/bin/env python3
"""
Seed reference catalogs (business categories, countries, locales, timezones).

Usage:
    python ops/scripts/seed_reference_catalogs.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ops" / "data"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL not set")

    categories = _load_json(DATA_DIR / "business_categories.json")
    reference = _load_json(DATA_DIR / "reference_catalogs.json")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for item in categories:
        cur.execute(
            "SELECT 1 FROM public.business_categories WHERE code = %s",
            (item["code"],),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO public.business_categories (id, code, name, description, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), %s, %s, %s, true, now(), now());
            """,
            (item["code"], item["name"], item["description"]),
        )

    for item in reference.get("countries", []):
        cur.execute(
            "SELECT 1 FROM public.countries WHERE code = %s",
            (item["code"],),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO public.countries (code, name, active)
            VALUES (%s, %s, true);
            """,
            (item["code"], item["name"]),
        )

    for item in reference.get("locales", []):
        cur.execute(
            "SELECT 1 FROM public.locales WHERE code = %s",
            (item["code"],),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO public.locales (code, name, active)
            VALUES (%s, %s, true);
            """,
            (item["code"], item["name"]),
        )

    for item in reference.get("timezones", []):
        cur.execute(
            "SELECT 1 FROM public.timezones WHERE name = %s",
            (item["name"],),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO public.timezones (name, display_name, offset_minutes, active)
            VALUES (%s, %s, %s, true);
            """,
            (item["name"], item["display_name"], item["offset_minutes"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Seed completed.")


if __name__ == "__main__":
    main()
