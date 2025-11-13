"""
Bowler codemod to replace duplicated helpers with canonical ones.

Fill REPLACEMENTS with (from_module, name) -> (to_module, name)
"""

from bowler import Query

REPLACEMENTS = {
    ("backend.app.core.refresh", "_now_ts"): (
        "apps.backend.app.shared.utils",
        "utcnow_iso",
    ),
    ("backend.app.core.login_rate_limit", "_now"): (
        "apps.backend.app.shared.utils",
        "utcnow_iso",
    ),
    ("backend.app.modules.identity.infrastructure.jwt_service", "_now"): (
        "apps.backend.app.shared.utils",
        "utcnow_iso",
    ),
}


def main() -> None:
    q = Query("apps/backend/app/**/*.py")
    for (mod_from, name_from), (mod_to, name_to) in REPLACEMENTS.items():
        q = q.select(f"{mod_from}:{name_from}").rename(name_to).rename_module(mod_to)
    q.execute(write=True, interactive=False)


if __name__ == "__main__":
    main()
