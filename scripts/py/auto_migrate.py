"""
Auto-migration runner for ops/migrations/* folders.

Behavior:
- Scans ops/migrations/* folders in lexicographic order (timestamped).
- Executes up.sql for each folder against the provided Postgres DSN.
- Intended to be idempotent if SQL uses IF NOT EXISTS guards.

Usage:
  DB_DSN=postgresql://user:pass@host/db python scripts/py/auto_migrate.py
  python scripts/py/auto_migrate.py --dsn postgresql://user:pass@host/db

Notes:
- Safe to run at container start when guarded with env flags (e.g., RUN_MIGRATIONS=1).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable


def _connect(dsn: str):
    try:
        import psycopg

        return psycopg.connect(dsn)
    except ImportError:
        try:
            import psycopg2  # type: ignore

            return psycopg2.connect(dsn)
        except ImportError as e:
            raise SystemExit(
                "Install psycopg or psycopg2-binary to use auto_migrate"
            ) from e


def _iter_migration_dirs(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and (p / "up.sql").exists()])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dsn", default=os.environ.get("DB_DSN", ""))
    p.add_argument("--dir", default="ops/migrations", help="Root migrations dir")
    args = p.parse_args()

    if not args.dsn:
        raise SystemExit("Provide --dsn or set DB_DSN env var")

    root = Path(args.dir)
    conn = _connect(args.dsn)
    # Run in autocommit mode so each statement is its own transaction.
    # This avoids leaving the connection in a failed transaction state
    # and supports operations like CREATE INDEX CONCURRENTLY.
    try:
        conn.autocommit = True  # psycopg2/psycopg3 compatible
    except Exception:
        pass

    try:
        with conn.cursor() as cur:

            def _split_sql_statements(sql: str) -> list[str]:
                stmts: list[str] = []
                buf: list[str] = []
                in_single = False
                in_double = False
                in_line_comment = False
                in_block_comment = False
                dollar_tag: str | None = None

                i = 0
                n = len(sql)
                while i < n:
                    ch = sql[i]
                    nxt = sql[i + 1] if i + 1 < n else ""

                    # Handle end of line comment
                    if in_line_comment:
                        buf.append(ch)
                        if ch == "\n":
                            in_line_comment = False
                        i += 1
                        continue

                    # Handle end of block comment
                    if in_block_comment:
                        buf.append(ch)
                        if ch == "*" and nxt == "/":
                            buf.append(nxt)
                            i += 2
                            in_block_comment = False
                            continue
                        i += 1
                        continue

                    # Enter comments (only when not inside quotes/dollar)
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

                    # Dollar-quoted strings
                    if not (in_single or in_double) and ch == "$":
                        # Attempt to read a tag $tag$
                        j = i + 1
                        while j < n and (sql[j].isalnum() or sql[j] == "_"):
                            j += 1
                        if j < n and sql[j] == "$":
                            tag = sql[i : j + 1]  # includes both $'s
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
                        # Not a dollar tag; fall through

                    # String literals
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

                    # Statement separator
                    if ch == ";" and not (
                        in_single
                        or in_double
                        or dollar_tag
                        or in_line_comment
                        or in_block_comment
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

            def _strip_sql_comments(s: str) -> str:
                import re

                # Remove /* ... */ blocks
                s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
                # Remove -- comments per line
                s = "\n".join([ln.split("--", 1)[0] for ln in s.splitlines()])
                return s.strip()

            # Helper: detect benign idempotency errors from psycopg/psycopg2
            def _is_idempotent_error(exc: Exception, stmt: str | None = None) -> bool:
                try:
                    # psycopg3
                    from psycopg.errors import (
                        DuplicateTable as PG3DuplicateTable,  # type: ignore
                        DuplicateObject as PG3DuplicateObject,  # type: ignore
                        DuplicateSchema as PG3DuplicateSchema,  # type: ignore
                    )

                    if isinstance(
                        exc, (PG3DuplicateTable, PG3DuplicateObject, PG3DuplicateSchema)
                    ):
                        return True
                except Exception:
                    pass
                try:
                    # psycopg2
                    from psycopg2.errors import (  # type: ignore
                        DuplicateTable as PG2DuplicateTable,
                        DuplicateObject as PG2DuplicateObject,
                        DuplicateSchema as PG2DuplicateSchema,
                    )

                    if isinstance(
                        exc, (PG2DuplicateTable, PG2DuplicateObject, PG2DuplicateSchema)
                    ):
                        return True
                except Exception:
                    pass

                msg = str(exc).lower()
                # Common localized phrases seen from Postgres server messages
                phrases = [
                    "already exists",  # en
                    "duplicate",  # en
                    "ya existe",  # es
                    "já existe",  # pt
                    "existe déjà",  # fr
                    "existiert bereits",  # de
                ]
                if any(p in msg for p in phrases):
                    return True
                # Treat missing object as idempotent only for DROP statements
                missing_phrases = [
                    "does not exist",
                    "no existe",
                    "n'existe pas",
                    "existiert nicht",
                ]
                if stmt is not None:
                    s = stmt.strip().lower()
                    if any(p in msg for p in missing_phrases) and (
                        s.startswith("drop ")
                        or s.startswith("drop index")
                        or (s.startswith("alter table") and " drop " in s)
                    ):
                        return True
                    # COMMENT ON COLUMN for a column that might not exist anymore
                    if any(p in msg for p in missing_phrases) and s.startswith(
                        "comment on "
                    ):
                        return True
                    # Primary key already present; adding again is benign
                    pk_phrases = [
                        "multiple primary keys",  # en
                        "múltiples llaves primarias",  # es (mensaje común)
                        "multiples llaves primarias",  # es (sin tilde)
                        "múltiples claves primarias",  # es (clave/llave)
                        "multiples claves primarias",  # es (sin tilde)
                    ]
                    if ("primary key" in s) and any(p in msg for p in pk_phrases):
                        return True
                return False

            for mig in _iter_migration_dirs(root):
                mig_name = mig.name
                # Guard: skip baseline schema migration if DB isn't empty or core tables already exist
                # This prevents FK/column errors when applying a full dump-like migration onto a live schema.
                if ("baseline_full_schema" in mig_name) and os.environ.get(
                    "FORCE_BASELINE", "0"
                ) not in ("1", "true", "TRUE"):
                    # If any well-known core/admin tables exist, skip baseline to avoid conflicts
                    try:
                        cur.execute(
                            """
                                SELECT EXISTS (
                                  SELECT 1 FROM information_schema.tables
                                  WHERE table_schema = 'public' AND table_name IN (
                                    'core_empresa','auth_user','usuarios_usuarioempresa','tenants'
                                  )
                                )
                                """
                        )
                        exists = bool(cur.fetchone()[0])
                    except Exception:
                        exists = False
                    if exists:
                        print(
                            f"Skip (baseline detected existing schema markers): {mig_name}"
                        )
                        continue

                raw_sql = (mig / "up.sql").read_text(encoding="utf-8")
                up_sql = raw_sql.strip()
                effective = _strip_sql_comments(up_sql)
                if not effective:
                    print(f"Skip (empty up.sql): {mig.name}")
                    continue
                # Execute statement-by-statement so duplicate/object-exists errors don't block the rest
                statements = _split_sql_statements(up_sql)
                if not statements:
                    print(f"Skip (empty up.sql): {mig.name}")
                    continue
                applied_any = False
                hard_error = None
                for idx, stmt in enumerate(statements, start=1):
                    try:
                        # Skip statements that are only comments/whitespace
                        stripped = _strip_sql_comments(stmt)
                        if not stripped:
                            continue
                        s_low = stripped.strip().lower().rstrip(";")
                        # Ignore explicit transaction control; we run in autocommit per statement
                        if s_low in ("begin", "commit", "rollback", "end"):
                            continue
                        cur.execute(stripped)
                        applied_any = True
                    except Exception as e:
                        if _is_idempotent_error(e, stmt):
                            # Skip benign duplicates and proceed; if we were inside a tx, ensure cleanup
                            try:
                                cur.execute("ROLLBACK")
                            except Exception:
                                pass
                            continue
                        hard_error = (idx, e)
                        break
                # Report outcome per migration
                if hard_error is None:
                    print(f"Applied: {mig.name}")
                else:
                    idx, e = hard_error
                    # Provide context about where it failed
                    print(f"Error in migration {mig.name} at statement #{idx}")
                    # Re-raise the original exception for visibility
                    raise e
        print("Auto-migrate done")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
