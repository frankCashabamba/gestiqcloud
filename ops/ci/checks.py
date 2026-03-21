"""
Repository sanity checks for db-pipeline CI.
"""

import re
import subprocess
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def check_duplicate_slots() -> list[str]:
    """Detect migrations with the same date+slot prefix."""
    errors = []
    seen: dict[str, str] = {}

    for d in sorted(MIGRATIONS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        # Extract date_slot prefix (e.g., "2026-03-06_001")
        parts = d.name.split("_", 3)
        if len(parts) >= 3:
            prefix = f"{parts[0]}_{parts[1]}"
            if prefix in seen:
                errors.append(
                    f"Duplicate slot {prefix}: '{seen[prefix]}' and '{d.name}'"
                )
            seen[prefix] = d.name

    return errors


def check_down_sql_coverage() -> list[str]:
    """Warn about recent migrations without down.sql."""
    warnings = []
    dirs = sorted(
        d for d in MIGRATIONS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )

    # Only check last 20 migrations
    recent = dirs[-20:] if len(dirs) > 20 else dirs
    for d in recent:
        if not (d / "down.sql").exists() and (d / "up.sql").exists():
            warnings.append(f"{d.name}: missing down.sql")

    return warnings


def check_no_modified_migrations() -> list[str]:
    """Fail if any existing migration's up.sql was modified (not newly added).

    Editing an already-applied migration means prod DB and the file are out of sync.
    New migrations (Added) are fine — only Modified ones are a problem.
    """
    errors = []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=M", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        modified = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        return []  # Not in a git context (e.g. local run without remote), skip

    for path_str in modified:
        p = Path(path_str)
        parts = p.parts
        if len(parts) >= 3 and parts[0] == "ops" and parts[1] == "migrations" and p.name == "up.sql":
            errors.append(
                f"Modified existing migration: {p}\n"
                "  Never edit an applied migration — create a new one instead."
            )

    return errors


def main() -> int:
    if not MIGRATIONS_DIR.exists():
        print("ops/ci/checks.py: No migrations dir. OK")
        return 0

    errors = check_duplicate_slots()
    errors += check_no_modified_migrations()
    warnings = check_down_sql_coverage()

    if warnings:
        print(f"{len(warnings)} warning(s) (missing down.sql):")
        for w in warnings:
            print(f"  ⚠ {w}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print("ops/ci/checks.py: OK ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
