# -*- coding: utf-8 -*-
"""
Bootstrap script for the Imports pipeline.

Key improvements in this refactor:
- Structured logging with levels (INFO/DEBUG/WARN/ERROR) and JSON-friendly lines.
- Safer SQL splitter (keeps dollar-quoted bodies, quotes, comments handling).
- Idempotent error detector expanded and centralized.
- Environment/CLI flags: --check-only, --dry-run, --verbose, --quiet.
- Defensive migration application: each statement isolated, BEGIN/COMMIT skipped.
- Schema checks separated and strictly typed; index detection more robust.
- Early exits when IMPORTS_ENABLED is falsy.

Usage examples:
  DB_DSN=postgresql://user:pass@host/db python scripts/py/bootstrap_imports.py
  python scripts/py/bootstrap_imports.py --dsn postgresql://user:pass@host/db --dir ops/migrations
  python scripts/py/bootstrap_imports.py --dsn postgresql://.. --check-only  # only verify schema
  python scripts/py/bootstrap_imports.py --dsn ... --dry-run --verbose       # plan only
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

# ---------------------------- Logging helpers -----------------------------


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "y", "t")


def _log(level: str, msg: str, **kv) -> None:
    record = {"level": level.upper(), "msg": msg, **kv}
    try:
        print(json.dumps(record, ensure_ascii=False))
    except Exception:
        # Fallback to plain text
        extra = " ".join(f"{k}={v}" for k, v in kv.items())
        print(f"[{level}] {msg} {extra}")


def log_info(msg: str, **kv) -> None:
    if not _env_bool("QUIET", False):
        _log("INFO", msg, **kv)


def log_debug(msg: str, **kv) -> None:
    if _env_bool("VERBOSE", False) and not _env_bool("QUIET", False):
        _log("DEBUG", msg, **kv)


def log_warn(msg: str, **kv) -> None:
    _log("WARN", msg, **kv)


def log_error(msg: str, **kv) -> None:
    _log("ERROR", msg, **kv)


# ---------------------------- DB connectivity -----------------------------


def _connect_psycopg(dsn: str):
    """Return a direct psycopg/psycopg2 connection for executing raw SQL."""
    try:
        import psycopg

        return psycopg.connect(dsn)
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2.connect(dsn)
        except ImportError as e:
            raise SystemExit(
                "Install psycopg or psycopg2-binary to use bootstrap_imports"
            ) from e


# ---------------------------- Migrations utils ----------------------------


def _iter_migration_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and (p / "up.sql").exists()])


def _strip_sql_comments(s: str) -> str:
    import re

    # Remove block comments and end-of-line comments, preserving content elsewhere
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = "\n".join([ln.split("--", 1)[0] for ln in s.splitlines()])
    return s.strip()


def _split_sql_statements(sql: str) -> List[str]:
    """Split SQL into statements by semicolon, respecting quotes and dollar tags."""
    stmts: List[str] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: Optional[str] = None

    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(ch)
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            buf.append(ch)
            if ch == "*" and nxt == "/":
                buf.append(nxt)
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if not (in_single or in_double or dollar_tag):
            if ch == "-" and nxt == "-":
                in_line_comment = True
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue

        if not (in_single or in_double) and ch == "$":
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < n and sql[j] == "$":
                tag = sql[i : j + 1]
                if dollar_tag is None:
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                elif dollar_tag == tag:
                    dollar_tag = None
                    buf.append(tag)
                    i = j + 1
                    continue

        if dollar_tag is None:
            if ch == "'" and not in_double:
                in_single = not in_single
                buf.append(ch)
                i += 1
                continue
            if ch == '"' and not in_single:
                in_double = not in_double
                buf.append(ch)
                i += 1
                continue

        if ch == ";" and not (
            in_single or in_double or dollar_tag or in_line_comment or in_block_comment
        ):
            stmt = "".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _is_idempotent_error(exc: Exception, stmt: Optional[str] = None) -> bool:
    """Return True if the error can be ignored when re-applying migrations."""
    # psycopg 3
    try:
        from psycopg.errors import (  # type: ignore
            DuplicateColumn,
            DuplicateDatabase,
            DuplicateObject,
            DuplicateSchema,
            DuplicateTable,
            UniqueViolation,
        )

        if isinstance(
            exc,
            (
                DuplicateTable,
                DuplicateObject,
                DuplicateSchema,
                DuplicateColumn,
                DuplicateDatabase,
                UniqueViolation,
            ),
        ):
            return True
    except Exception:
        pass

    # psycopg2
    try:
        from psycopg2.errors import DuplicateColumn as D2C
        from psycopg2.errors import DuplicateDatabase as D2DB
        from psycopg2.errors import DuplicateObject as D2O
        from psycopg2.errors import DuplicateSchema as D2S
        from psycopg2.errors import DuplicateTable as D2T  # type: ignore
        from psycopg2.errors import UniqueViolation as D2U

        if isinstance(exc, (D2T, D2O, D2S, D2C, D2DB, D2U)):
            return True
    except Exception:
        pass

    # Message heuristics
    msg = str(exc).lower()
    if any(
        p in msg
        for p in (
            "already exists",
            "duplicate",
            "ya existe",
            "j\u00e1 existe",
            "existe d\u00e9j\u00e0",
            "existiert bereits",
        )
    ):
        return True

    # DROP/COMMENT ON when target doesn't exist is idempotent
    missing = ("does not exist", "no existe", "n'existe pas", "existiert nicht")
    if stmt is not None:
        s = stmt.strip().lower()
        if any(p in msg for p in missing) and (
            s.startswith("drop ")
            or s.startswith("drop index")
            or (s.startswith("alter table") and " drop " in s)
            or s.startswith("comment on ")
        ):
            return True
        if ("primary key" in s) and any(
            p in msg
            for p in (
                "multiple primary keys",
                "m\u00faltiples llaves primarias",
                "multiples llaves primarias",
                "m\u00faltiples claves primarias",
                "multiples claves primarias",
            )
        ):
            return True
    return False


# ---------------------------- Auto-migrate core ----------------------------


def _auto_migrate(dsn: str, root_dir: Path, *, dry_run: bool = False) -> None:
    conn = _connect_psycopg(dsn)
    try:
        # Autocommit so each statement is isolated
        try:
            conn.autocommit = True  # psycopg/psycopg2 compatible
        except Exception:
            pass

        with conn.cursor() as cur:

            def _table_exists(table_name: str) -> bool:
                try:
                    cur.execute(
                        """
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = %s
                        LIMIT 1
                        """,
                        (table_name,),
                    )
                    return cur.fetchone() is not None
                except Exception:
                    return False

            # Ensure tracking table exists with extended metadata
            try:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(255) UNIQUE NOT NULL
                    );
                    """
                )
                for alter in (
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS name TEXT;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS status TEXT;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS mode TEXT;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS executed_by TEXT;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS error_message TEXT;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS applied_order INTEGER;",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();",
                    "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
                ):
                    cur.execute(alter)
            except Exception as e:
                log_warn("schema_migrations alter failed (non-fatal)", error=str(e))

            # Preload statuses
            applied_success: set[str] = set()
            applied_ignored: set[str] = set()
            applied_failed: set[str] = set()
            try:
                cur.execute("SELECT version, status FROM schema_migrations")
                for v, st in cur.fetchall():
                    st_low = str(st).lower() if st is not None else ""
                    v_str = str(v)
                    if st_low == "success":
                        applied_success.add(v_str)
                    elif st_low == "ignored":
                        applied_ignored.add(v_str)
                    elif st_low == "failed":
                        applied_failed.add(v_str)
            except Exception:
                applied_success = set()
                applied_ignored = set()
                applied_failed = set()

            force_reapply = _env_bool("OPS_MIG_FORCE_REAPPLY", False)
            skip_failed = _env_bool("OPS_MIG_SKIP_FAILED", False)

            for mig in _iter_migration_dirs(root_dir):
                version = mig.name
                parts = version.split("_", 2)
                friendly = parts[2] if len(parts) >= 3 else version

                # Skip if success present and not forced
                if (version in applied_success) and not force_reapply:
                    log_info("migration skipped (already applied)", version=version)
                    try:
                        cur.execute(
                            """
                            INSERT INTO schema_migrations(version, name, status, completed_at, updated_at)
                            VALUES (%s, %s, 'success', NOW(), NOW())
                            ON CONFLICT (version) DO NOTHING;
                            """,
                            (version, friendly),
                        )
                    except Exception:
                        pass
                    continue

                if (version in applied_ignored) and not force_reapply:
                    log_info("migration skipped (ignored)", version=version)
                    try:
                        cur.execute(
                            """
                            INSERT INTO schema_migrations(version, name, status, updated_at)
                            VALUES (%s, %s, 'ignored', NOW())
                            ON CONFLICT (version) DO UPDATE SET
                                name = EXCLUDED.name,
                                status = 'ignored',
                                updated_at = NOW();
                            """,
                            (version, friendly),
                        )
                    except Exception:
                        pass
                    continue

                if skip_failed and (version in applied_failed) and not force_reapply:
                    log_warn(
                        "migration skipped (previously failed and OPS_MIG_SKIP_FAILED=1)",
                        version=version,
                    )
                    continue

                raw_sql = (mig / "up.sql").read_text(encoding="utf-8")
                up_sql = raw_sql.strip()
                effective = _strip_sql_comments(up_sql)
                if not effective:
                    log_info("migration skipped (empty up.sql)", version=version)
                    continue

                statements = _split_sql_statements(up_sql)
                if not statements:
                    log_info("migration skipped (no statements)", version=version)
                    continue

                # Guard: skip legacy migrations that reference missing legacy tables on a fresh DB
                eff_low = effective.lower()
                legacy_refs = [
                    ("facturas", "facturas"),
                    ("public.facturas", "facturas"),
                    (" payments", "payments"),
                    ("\tpayments", "payments"),
                    ("public.payments", "payments"),
                ]
                missing_legacy = None
                for marker, tbl in legacy_refs:
                    if marker in eff_low and not _table_exists(tbl):
                        missing_legacy = tbl
                        break
                if missing_legacy is not None:
                    log_info(
                        "migration ignored (references missing legacy table)",
                        version=version,
                        missing_table=missing_legacy,
                    )
                    try:
                        cur.execute(
                            """
                            INSERT INTO schema_migrations(version, name, status, completed_at, updated_at)
                            VALUES (%s, %s, 'ignored', NOW(), NOW())
                            ON CONFLICT (version) DO UPDATE SET
                                name = EXCLUDED.name,
                                status = 'ignored',
                                completed_at = NOW(),
                                updated_at = NOW();
                            """,
                            (version, friendly),
                        )
                    except Exception:
                        pass
                    continue

                start_ns = time.perf_counter_ns()
                hard_error: Optional[Tuple[int, Exception]] = None

                # Ensure tracking row exists (pending)
                try:
                    cur.execute(
                        """
                        INSERT INTO schema_migrations(version, name, status, applied_order)
                        VALUES (%s, %s, 'pending', (
                            SELECT COALESCE(MAX(applied_order), 0) + 1 FROM schema_migrations
                        ))
                        ON CONFLICT (version) DO NOTHING;
                        """,
                        (version, friendly),
                    )
                except Exception:
                    pass

                # Apply statements
                for idx, stmt in enumerate(statements, start=1):
                    stripped = _strip_sql_comments(stmt)
                    if not stripped:
                        continue
                    s_low = stripped.strip().lower().rstrip(";")
                    if s_low in ("begin", "commit", "rollback", "end"):
                        continue

                    if dry_run:
                        log_debug(
                            "dry-run: statement planned", version=version, idx=idx
                        )
                        continue

                    try:
                        log_info(
                            "executing sql",
                            version=version,
                            idx=idx,
                            statement=stripped,
                        )
                        cur.execute(stripped)
                    except Exception as e:
                        if _is_idempotent_error(e, stmt):
                            # Ensure transaction is clean for next stmts
                            try:
                                cur.execute("ROLLBACK")
                            except Exception:
                                pass
                            log_debug(
                                "idempotent error ignored",
                                version=version,
                                idx=idx,
                                error=str(e),
                            )
                            continue
                        hard_error = (idx, e)
                        break

                elapsed_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

                if hard_error is None:
                    log_info("migration applied", version=version, ms=elapsed_ms)
                    try:
                        cur.execute(
                            """
                            INSERT INTO schema_migrations(version, name, status, execution_time_ms, completed_at, updated_at)
                            VALUES (%s, %s, 'success', %s, NOW(), NOW())
                            ON CONFLICT (version) DO UPDATE SET
                                name = EXCLUDED.name,
                                status = 'success',
                                execution_time_ms = EXCLUDED.execution_time_ms,
                                completed_at = NOW(),
                                updated_at = NOW();
                            """,
                            (version, friendly, elapsed_ms),
                        )
                    except Exception as e:
                        log_warn(
                            "failed to update schema_migrations row",
                            version=version,
                            error=str(e),
                        )
                else:
                    idx, e = hard_error
                    log_error(
                        "migration failed", version=version, stmt_idx=idx, error=str(e)
                    )
                    try:
                        cur.execute(
                            """
                            INSERT INTO schema_migrations(version, name, status, error_message, updated_at)
                            VALUES (%s, %s, 'failed', %s, NOW())
                            ON CONFLICT (version) DO UPDATE SET
                                name = EXCLUDED.name,
                                status = 'failed',
                                error_message = LEFT(EXCLUDED.error_message, 1000),
                                updated_at = NOW();
                            """,
                            (version, friendly, str(e)),
                        )
                    except Exception:
                        pass
                    raise e
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------- Schema checks -------------------------------

REQUIRED_TABLES: Dict[str, List[str]] = {
    # UUID multi-tenant schema
    "import_batches": ["id", "tenant_id", "source_type", "origin", "status"],
    "import_items": ["id", "batch_id", "idx", "raw", "status", "idempotency_key"],
    "import_mappings": ["id", "tenant_id", "name", "source_type"],
    "import_item_corrections": ["id", "tenant_id", "item_id", "user_id", "field"],
    "import_lineage": ["id", "tenant_id", "item_id", "promoted_to"],
    "auditoria_importacion": [
        "id",
        "tenant_id",
        "documento_id",
        "fecha",
        "batch_id",
        "item_id",
    ],
}

REQUIRED_INDEXES: Dict[str, List[Tuple[str, str]]] = {
    "import_items": [
        ("unique", "idempotency_key"),
        ("index", "batch_id"),
        ("index", "dedupe_hash"),
    ]
}


def _engine(dsn: str) -> Engine:
    url = make_url(dsn)
    if url.get_backend_name() not in (
        "postgresql",
        "postgresql+psycopg2",
        "postgresql+psycopg",
    ):
        raise SystemExit("This checker is intended for PostgreSQL DSNs.")
    return create_engine(dsn, future=True)


@dataclass
class SchemaCheckResult:
    missing_tables: List[str]
    missing_columns_or_indexes: List[str]


def _check_schema(dsn: str) -> SchemaCheckResult:
    engine = _engine(dsn)
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

    # Indexes: We look into pg_indexes definition, matching both column and uniqueness
    with engine.connect() as conn:
        for tbl, rules in REQUIRED_INDEXES.items():
            for kind, col in rules:
                if kind == "unique":
                    q = text(
                        """
                        SELECT 1
                        FROM pg_indexes i
                        WHERE i.tablename = :tbl
                          AND i.indexdef ILIKE '%UNIQUE%'
                          AND i.indexdef ILIKE '%' || :col || '%'
                        LIMIT 1
                        """
                    )
                else:
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
    return SchemaCheckResult(missing_tables, missing_columns)


# ---------------------------- CLI / entrypoint ----------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", default=os.environ.get("DB_DSN", ""))
    p.add_argument("--dir", default=os.environ.get("MIGRATIONS_DIR", "ops/migrations"))
    p.add_argument("--check-only", action="store_true")
    p.add_argument(
        "--dry-run", action="store_true", help="Plan migrations without executing them"
    )
    p.add_argument("--verbose", action="store_true", help="Verbose/debug logging")
    p.add_argument(
        "--quiet", action="store_true", help="Minimal output (overrides verbose)"
    )
    args = p.parse_args()

    # Reflect flags into env-backed toggles (so helpers can read them)
    if args.verbose:
        os.environ["VERBOSE"] = "1"
    if args.quiet:
        os.environ["QUIET"] = "1"

    imports_enabled = os.environ.get("IMPORTS_ENABLED", "1").lower() in (
        "1",
        "true",
        "yes",
    )
    if not imports_enabled:
        log_info("imports disabled; skipping bootstrap")
        return 0

    if not args.dsn:
        raise SystemExit("Provide --dsn or set DB_DSN env var")

    # Apply migrations unless check-only
    if not args.check_only:
        log_info("starting auto-migrate", dir=args.dir, dry_run=args.dry_run)
        _auto_migrate(args.dsn, Path(args.dir), dry_run=args.dry_run)

    # Verify schema
    res = _check_schema(args.dsn)
    if not res.missing_tables and not res.missing_columns_or_indexes:
        log_info("OK: imports schema present")
        return 0

    if res.missing_tables:
        log_warn("Missing tables", missing=res.missing_tables)
        for t in res.missing_tables:
            print(" -", t)
    if res.missing_columns_or_indexes:
        log_warn("Missing columns/indexes", missing=res.missing_columns_or_indexes)
        for c in res.missing_columns_or_indexes:
            print(" -", c)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
