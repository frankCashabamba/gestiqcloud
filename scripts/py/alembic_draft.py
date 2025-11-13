from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
import subprocess


def main():
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "apps" / "backend"
    alembic_ini = backend_dir / "alembic.ini"
    if not alembic_ini.exists():
        print("alembic.ini not found at", alembic_ini, file=sys.stderr)
        sys.exit(1)

    # Ensure DATABASE_URL exists
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print(
            "Set DATABASE_URL to your Postgres DSN (e.g., postgresql://...)",
            file=sys.stderr,
        )
        sys.exit(2)

    # Create revision via autogenerate in backend/alembic/versions
    rev_msg = f"draft_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    cmd = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(alembic_ini),
        "revision",
        "--autogenerate",
        "-m",
        rev_msg,
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(backend_dir))

    print("\nDraft revision created under apps/backend/alembic/versions.")
    print("Review it, then translate into ops/migrations as SQL for production.")


if __name__ == "__main__":
    main()
