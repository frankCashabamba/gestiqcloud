from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parents[2]
    baseline_dir = (
        repo_root / "ops" / "migrations" / "2025-09-22_000_baseline_full_schema"
    )
    out_file = baseline_dir / "up.sql"

    dsn = os.environ.get("DB_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        print(
            "Set DB_DSN or DATABASE_URL to your Postgres DSN (e.g., postgresql://user:pass@host:5432/db)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Requires pg_dump in PATH
    cmd = [
        "pg_dump",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        dsn,
    ]
    print("Running:", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print(
            "pg_dump not found. Install PostgreSQL client tools and ensure pg_dump is in PATH.",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.CalledProcessError as e:
        print("pg_dump failed:", e.stderr or e.stdout, file=sys.stderr)
        sys.exit(e.returncode or 3)

    raw = result.stdout.splitlines()

    def _clean(lines: list[str]) -> list[str]:
        out: list[str] = []
        skip_prefixes = (
            "SET ",
            "SELECT pg_catalog.set_config",
            "COMMENT ON EXTENSION",
            "COMMENT ON SCHEMA",
            "ALTER SCHEMA ",
            "ALTER TABLE ",  # OWNER TO ...
            "ALTER SEQUENCE ",
            "ALTER FUNCTION ",
            "REVOKE ",
            "GRANT ",
        )
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            if s.startswith("--"):
                continue
            if any(s.startswith(pfx) for pfx in skip_prefixes):
                continue
            # drop CREATE EXTENSION lines from dump; we'll add curated ones
            if s.upper().startswith("CREATE EXTENSION "):
                continue
            # avoid schema create for public
            if s.upper().startswith("CREATE SCHEMA PUBLIC"):
                continue
            out.append(ln)
        return out

    cleaned = _clean(raw)

    header = (
        "-- Generated baseline schema via pg_dump --schema-only --no-owner --no-privileges\n"
        "-- Cleaned to remove env-specific statements (SET/OWNER/GRANT/etc.)\n"
        "-- Review before applying in production.\n\n"
    )

    # curated extensions at top (idempotent)
    ext_block = (
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";\n'
        'CREATE EXTENSION IF NOT EXISTS "pgcrypto";\n\n'
    )
    baseline_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        header + ext_block + "\n".join(cleaned) + "\n", encoding="utf-8"
    )
    print(f"Baseline written to {out_file}")


if __name__ == "__main__":
    main()
