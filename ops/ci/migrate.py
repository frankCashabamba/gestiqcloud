"""
Smoke migration runner for CI.

For now, this is a placeholder that verifies the folder layout exists.
Later, it can apply SQL migrations in ops/migrations/* to a temp database.
"""

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    mig = root / "migrations"
    if not mig.exists():
        print("No migrations folder found (ops/migrations). Skipping.")
        return 0
    print("Found migrations folder:", mig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
