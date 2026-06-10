"""
CI migration validator: checks folder layout and SQL syntax basics.
"""

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print("No migrations folder found (ops/migrations). Skipping.")
        return 0

    errors = []
    migration_dirs = sorted(
        d for d in MIGRATIONS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )

    if not migration_dirs:
        print("No migration directories found.")
        return 0

    name_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{3}_[a-z0-9_]+$")

    for d in migration_dirs:
        up_sql = d / "up.sql"

        # Check naming convention
        if not name_pattern.match(d.name):
            errors.append(f"{d.name}: does not follow YYYY-MM-DD_NNN_slug naming convention")

        # Check up.sql exists
        if not up_sql.exists():
            errors.append(f"{d.name}: missing up.sql")
            continue

        content = up_sql.read_text(encoding="utf-8")

        # Check not empty
        if not content.strip():
            errors.append(f"{d.name}: up.sql is empty")

        # Check for dangerous patterns
        if "|| true" in content or "|| TRUE" in content:
            errors.append(f"{d.name}: up.sql contains error-silencing pattern '|| true'")

    print(f"Checked {len(migration_dirs)} migrations")

    if errors:
        print(f"\n{len(errors)} issue(s) found:")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print("All migrations pass CI checks ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
