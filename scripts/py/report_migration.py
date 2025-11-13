"""
Migration status report for backend refactor.

Usage:
  python scripts/py/report_migration.py

Outputs a summary of:
  - Repositories using CRUDBase
  - ping_* endpoints unified to shared.utils.ping_ok
  - Time helpers usages (now_ts vs legacy _now/_now_ts)
  - Duplicate functions summary (calls the existing scan_duplicates script)
"""

from __future__ import annotations

import os
import re
import fnmatch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
APP = ROOT / "apps" / "backend" / "app"

EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


def _python_grep(
    pattern: str, dirpath: Path, globs: tuple[str, ...] = ("*.py",)
) -> list[str]:
    rx = re.compile(pattern)
    results: list[str] = []
    for dpath, dnames, fnames in os.walk(dirpath):
        # prune excluded dirs
        dnames[:] = [d for d in dnames if d not in EXCLUDE_DIRS]
        # gather only wanted files
        wanted: set[str] = set()
        for g in globs:
            wanted.update(fnmatch.filter(fnames, g))
        for fname in wanted:
            f = Path(dpath) / fname
            try:
                with f.open("r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        if rx.search(line):
                            results.append(f"{f}:{i}:{line.rstrip()}")
            except OSError:
                continue
    return results


def rg(pattern: str, dir: Path, globs: tuple[str, ...] = ("*.py",)) -> list[str]:
    """
    Search files for a regex pattern.
    - Tries `rg` (ripgrep) first for speed.
    - Falls back to a pure-Python grep if `rg` isn't available.
    Returns a list of 'path:lineno:line' strings.
    """
    cmd = ["rg", "-n", "--no-heading", "-S", pattern, str(dir)]
    # include-only globs
    for g in globs:
        cmd += ["-g", g]
    # ignore noisy dirs
    for ex in EXCLUDE_DIRS:
        cmd += ["-g", f"!**/{ex}/**"]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        return [line for line in out.splitlines() if line.strip()]
    except FileNotFoundError:
        # ripgrep not installed → fallback
        return _python_grep(pattern, dir, globs)
    except subprocess.CalledProcessError:
        # ripgrep ran but found nothing
        return []


def report_crudbase() -> list[str]:
    # Match both subclassing with type args (CRUDBase[...]) and calls CRUDBase(...)
    hits = set(rg(r"CRUDBase\[", APP) + rg(r"CRUDBase\(", APP))
    return sorted(hits)


def report_pings() -> tuple[list[str], list[str]]:
    # FIX: use \w, not \\w
    defs = rg(r"def ping_\w+\(", APP)
    uses_ping_ok = rg(r"ping_ok\(\)", APP)
    return defs, uses_ping_ok


def report_time_helpers() -> tuple[list[str], list[str], list[str]]:
    use_now_ts = rg(r"now_ts\(", APP)
    legacy_now = rg(r"\b_now\(\)", APP)
    legacy_now_ts = rg(r"\b_now_ts\(\)", APP)
    return use_now_ts, legacy_now, legacy_now_ts


def report_duplicates() -> str:
    try:
        out = subprocess.check_output(
            ["python", str(ROOT / "scripts" / "py" / "scan_duplicates.py")], text=True
        )
        return out
    except Exception as e:
        return f"<error running scan_duplicates.py: {e}>"


def main() -> None:
    print("=== Migration Report ===")
    print(f"Repo root: {ROOT}")
    print(f"App path:  {APP}")

    print("\n-- CRUDBase usage --")
    crud_lines = report_crudbase()
    print(f"Files using CRUDBase: {len(crud_lines)}")
    for line in crud_lines:
        print(" ", line)

    print("\n-- Ping endpoints --")
    defs, uses = report_pings()
    print(f"ping_* definitions: {len(defs)}")
    print(f"ping_ok() usages:  {len(uses)}")

    print("\n-- Time helpers --")
    use_now_ts, legacy_now, legacy_now_ts = report_time_helpers()
    print(f"now_ts() uses:         {len(use_now_ts)}")
    print(f"legacy _now() calls:   {len(legacy_now)}")
    print(f"legacy _now_ts() calls:{len(legacy_now_ts)}")

    print("\n-- Duplicates (scan) --")
    dups = report_duplicates()
    lines = dups.splitlines()
    head = lines[:50]
    for line in head:
        print(line)
    if len(lines) > len(head):
        print(f"... ({len(lines) - len(head)} more lines)")


if __name__ == "__main__":
    main()
