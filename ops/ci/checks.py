"""
Lightweight repository checks used by db-pipeline CI.
Currently acts as a placeholder to keep the pipeline green while
we migrate real checks.
"""

import sys


def main() -> int:
    # TODO: add duplicate detection and folder sanity checks
    print("ops/ci/checks.py: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
