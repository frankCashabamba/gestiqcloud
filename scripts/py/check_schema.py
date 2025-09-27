"""
Schema checker for Imports pipeline (works locally or in Docker).

Usage examples:
  # Using env var DB_DSN
  python scripts/py/check_schema.py

  # Explicit DSN
  python scripts/py/check_schema.py --dsn postgresql://user:pass@localhost:5432/db

Exit code is non‑zero if required objects are missing (unless --allow-missing).
"""

from __future__ import annotations

import argparse
import os
from typing import Dict, List, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy import inspect as sa_inspect


REQUIRED_TABLES: Dict[str, List[str]] = {
    "import_batches": [
        "id",
        "empresa_id",
        "source_type",
        "origin",
        "file_key",
        "mapping_id",
        "status",
        "created_by",
        "created_at",
    ],
    "import_items": [
        "id",
        "batch_id",
        "idx",
        "raw",
        "normalized",
        "status",
        "errors",
        "dedupe_hash",
        "idempotency_key",
        "promoted_to",
        "promoted_id",
        "promoted_at",
    ],
    "import_mappings": [
        "id",
        "empresa_id",
        "name",
        "source_type",
        "version",
        "mappings",
        "transforms",
        "defaults",
        "dedupe_keys",
        "created_at",
    ],
    "import_item_corrections": [
        "id",
        "empresa_id",
        "item_id",
        "user_id",
        "field",
        "old_value",
        "new_value",
        "created_at",
    ],
    "import_lineage": [
        "id",
        "empresa_id",
        "item_id",
        "promoted_to",
        "promoted_ref",
        "created_at",
    ],
    "auditoria_importacion": [
        # legacy + new linkage
        "id",
        "documento_id",
        "empresa_id",
        "usuario_id",
        "cambios",
        "fecha",
        "batch_id",
        "item_id",
    ],
}

REQUIRED_INDEXES: Dict[str, List[Tuple[str, str]]] = {
    # table -> list of (kind, column/constraint)
    # kind in {unique, index}
    "import_items": [
        ("unique", "idempotency_key"),
        ("index", "batch_id"),
        ("index", "dedupe_hash"),
    ],
    "import_batches": [
        ("index", "empresa_id"),
    ],
}

# Exact index names we strongly prefer to exist (best effort)
REQUIRED_INDEX_NAMES: List[str] = [
    "ix_import_items_batch_idx",
    "ix_import_batches_empresa_created",
    "ux_import_items_batch_id_idem",
    "ix_import_items_promoted_hash",
]


def _connect(dsn: str) -> Engine:
    url = make_url(dsn)
    if url.get_backend_name() not in ("postgresql", "postgresql+psycopg2", "postgresql+psycopg"):
        raise SystemExit("This checker is intended for PostgreSQL DSNs.")
    return create_engine(dsn, future=True)


def check_schema(engine: Engine) -> Tuple[List[str], List[str]]:
    insp = sa_inspect(engine)
    tables = set(insp.get_table_names())
    missing_tables: List[str] = []
    missing_columns: List[str] = []

    for tbl, cols in REQUIRED_TABLES.items():
        if tbl not in tables:
            missing_tables.append(tbl)
            continue
        existing_cols = {c["name"] for c in insp.get_columns(tbl)}
        for c in cols:
            if c not in existing_cols:
                missing_columns.append(f"{tbl}.{c}")

    # Indexes/constraints (best effort using pg_catalog)
    with engine.connect() as conn:
        for tbl, rules in REQUIRED_INDEXES.items():
            for kind, col in rules:
                if kind == "unique":
                    q = text(
                        """
                        SELECT 1
                        FROM pg_indexes i
                        JOIN pg_class t ON t.relname = i.tablename
                        WHERE i.tablename = :tbl
                          AND i.indexdef ILIKE '%' || :col || '%'
                          AND i.indexdef ILIKE '%UNIQUE%'
                        LIMIT 1
                        """
                    )
                else:  # index
                    q = text(
                        """
                        SELECT 1
                        FROM pg_indexes i
                        WHERE i.tablename = :tbl
                          AND i.indexdef ILIKE '%' || :col || '%'
                        LIMIT 1
                        """
                    )
                ok = conn.execute(q, {"tbl": tbl, "col": col}).scalar() is not None
                if not ok:
                    missing_columns.append(f"{tbl} (missing {kind} on {col})")

        # Check by index name explicitly
        qnames = text(
            """
            SELECT indexname FROM pg_indexes WHERE indexname = ANY(:names)
            """
        )
        rows = conn.execute(qnames, {"names": REQUIRED_INDEX_NAMES}).fetchall()
        found = {r[0] for r in rows}
        for name in REQUIRED_INDEX_NAMES:
            if name not in found:
                missing_columns.append(f"index {name}")

    return missing_tables, missing_columns


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", default=os.environ.get("DB_DSN", ""))
    p.add_argument("--allow-missing", action="store_true")
    args = p.parse_args()

    if not args.dsn:
        raise SystemExit("Provide --dsn or set DB_DSN env var")

    engine = _connect(args.dsn)
    missing_tables, missing_columns = check_schema(engine)

    if not missing_tables and not missing_columns:
        print("OK: imports schema present")
        return 0

    if missing_tables:
        print("Missing tables:")
        for t in missing_tables:
            print(" -", t)
    if missing_columns:
        print("Missing columns/indexes:")
        for c in missing_columns:
            print(" -", c)

    if args.allow_missing:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
