"""
Bowler codemod to rewrite legacy imports to new app layout.

Examples:
- backend.app.* -> apps.backend.app.*
"""

from bowler import Query

RULES = [
    ("backend.app.", "apps.backend.app."),
]


def main() -> None:
    q = Query("apps/backend/app/**/*.py")
    for old, new in RULES:
        q = q.select_module(old.rstrip(".")).rename(new.rstrip("."))
    q.execute(write=True, interactive=False)


if __name__ == "__main__":
    main()
