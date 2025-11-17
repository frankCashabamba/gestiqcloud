#!/usr/bin/env python3
"""
Helper script to keep re-running `pre-commit run --all-files` until all hooks
stop modifying files and return success.

Usage: `python scripts/precommit_loop.py`
"""

import subprocess
import sys


def run_precommit() -> subprocess.CompletedProcess:
    print("\n> Running `pre-commit run --all-files`...")
    return subprocess.run(
        ["pre-commit", "run", "--all-files"],
        text=True,
        capture_output=True,
    )


def stage_paths() -> None:
    print("> Running `git add -u` to stage tracked changes...")
    subprocess.run(["git", "add", "-u"], check=True)


def has_unstaged_changes() -> bool:
    status = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=True,
    )
    return bool(status.stdout.strip())


def main() -> int:
    iteration = 0
    while True:
        iteration += 1
        cp = run_precommit()
        print(cp.stdout, cp.stderr, sep="")

        if cp.returncode == 0 and not has_unstaged_changes():
            print("\n✅ All hooks passed cleanly; no unstaged changes left.")
            return 0

        if cp.returncode != 0:
            print("> Hooks reported fixes; restaging and repeating.")
        else:
            print("> Hooks passed but there are still unstaged files. Restaging.")

        stage_paths()

        if iteration >= 10:
            print(
                "\n⚠️  The script has run 10 iterations; you may want to inspect "
                "the repo manually before continuing."
            )
            return 1


if __name__ == "__main__":
    sys.exit(main())
