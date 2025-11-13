#!/usr/bin/env python3
"""
Fix common mojibake in Spanish comments across the repo and ensure UTF-8.

Usage:
  python scripts/py/fix_mojibake_comments.py --dry-run
  python scripts/py/fix_mojibake_comments.py --apply

This script only touches comment lines (starting with optional whitespace + '#')
in source files (.py, .ts, .tsx). It replaces frequent mojibake artifacts
introduced by wrong charset roundtrips (e.g., 'almacAcn' -> 'almacén').

Safe by default: runs in dry-run unless --apply is passed.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXTS = {".py", ".ts", ".tsx"}

# Minimal, focused mapping for common artifacts seen in this repo.
REPLACEMENTS = {
    # words
    "almacAcn": "almacén",
    "almac�n": "almacén",
    "devoluciA3n": "devolución",
    "devoluci�n": "devolución",
    "impresiA3n": "impresión",
    "impresi�n": "impresión",
    "tAcrmica": "térmica",
    "t�rmica": "térmica",
    "lA-neas": "líneas",
    "l�neas": "líneas",
    "funciA3n": "función",
    "funci�n": "función",
    "nA�mero": "número",
    "n�mero": "número",
    "opciA3n": "opción",
    "opci�n": "opción",
    "explA-cito": "explícito",
    "expl�cito": "explícito",
    "envA-e": "envíe",
    "env�e": "envíe",
}

COMMENT_RE = re.compile(r"^\s*#")


def process_file(path: Path, apply: bool) -> tuple[int, int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return (0, 0)

    changed = False
    out_lines = []
    changed_lines = 0
    for line in text.splitlines(keepends=True):
        if COMMENT_RE.match(line):
            orig = line
            for bad, good in REPLACEMENTS.items():
                if bad in line:
                    line = line.replace(bad, good)
            if line != orig:
                changed = True
                changed_lines += 1
        out_lines.append(line)

    if changed and apply:
        Path(path).write_text("".join(out_lines), encoding="utf-8")
    return (1 if changed else 0, changed_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply changes in-place")
    ap.add_argument("--dry-run", action="store_true", help="dry-run (default)")
    ap.add_argument("--root", default=str(ROOT), help="repo root (auto)")
    args = ap.parse_args()
    apply = bool(args.apply and not args.dry_run)

    total_files = 0
    total_changed = 0
    total_lines = 0
    root = Path(args.root)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in EXTS:
            continue
        # skip venvs/node_modules/dist
        parts = set(p.parts)
        if {"node_modules", ".venv", "dist", "build"} & parts:
            continue
        ch, ch_lines = process_file(p, apply)
        total_files += 1
        total_changed += ch
        total_lines += ch_lines

    mode = "APPLY" if apply else "DRY-RUN"
    print(
        f"[{mode}] scanned={total_files} files, changed_files={total_changed}, changed_lines={total_lines}"
    )


if __name__ == "__main__":
    main()
