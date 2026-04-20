from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
TEST_DIRS = [BACKEND_ROOT / "app" / "tests", BACKEND_ROOT / "tests"]
GENERIC_STEMS = {
    "__init__",
    "admin",
    "api",
    "base",
    "config",
    "constants",
    "crud",
    "database",
    "helpers",
    "http",
    "interface",
    "main",
    "models",
    "router",
    "routes",
    "schema",
    "schemas",
    "service",
    "services",
    "tasks",
    "tenant",
    "types",
    "utils",
}
IGNORED_TOKENS = {
    "app",
    "apps",
    "backend",
    "application",
    "core",
    "db",
    "http",
    "infrastructure",
    "interface",
    "models",
    "modules",
    "ops",
    "platform",
    "routers",
    "scripts",
    "services",
    "shared",
    "tests",
}
SPECIAL_CASES: dict[str, list[str]] = {
    "ops/migrations/": [
        "app/tests/test_admin_ops_migrations.py",
        "app/tests/test_admin_config_migrations.py",
        "app/tests/test_smoke_pg.py",
        "app/tests/test_tenant_isolation.py",
    ],
    "ops/scripts/migrate_all_migrations_idempotent.py": [
        "app/tests/test_admin_ops_migrations.py",
        "app/tests/test_admin_config_migrations.py",
    ],
    "apps/backend/app/db/": [
        "app/tests/test_smoke_pg.py",
        "app/tests/test_tenant_isolation.py",
        "app/tests/test_smoke_pos_pg.py",
    ],
    "apps/backend/app/config/database.py": [
        "app/tests/test_admin_ops_migrations.py",
        "app/tests/test_smoke_pg.py",
    ],
}
MAX_SELECTED = 30
POSTGRES_TESTS = {
    "app/tests/test_admin_config_migrations.py",
    "app/tests/test_admin_ops_migrations.py",
    "app/tests/test_dashboard_kpis_panaderia.py",
    "app/tests/test_documents_persistence.py",
    "app/tests/test_importador_async_learning.py",
    "app/tests/test_importador_tasks_learning.py",
    "app/tests/test_inventory_adjust_metadata.py",
    "app/tests/test_inventory_costing.py",
    "app/tests/test_margins_analytics_pg.py",
    "app/tests/test_pos_backfill_tenant_isolation.py",
    "app/tests/test_pos_receipt_idempotency_pg.py",
    "app/tests/test_production_business_flow.py",
    "app/tests/test_smoke_pg.py",
    "app/tests/test_smoke_pos_pg.py",
    "app/tests/test_stock_transfers.py",
    "app/tests/test_tenant_isolation.py",
}
POSTGRES_SPECIAL_CASES: dict[str, list[str]] = {
    "ops/migrations/": [
        "app/tests/test_admin_config_migrations.py",
        "app/tests/test_admin_ops_migrations.py",
        "app/tests/test_smoke_pg.py",
        "app/tests/test_tenant_isolation.py",
    ],
    "ops/scripts/migrate_all_migrations_idempotent.py": [
        "app/tests/test_admin_config_migrations.py",
        "app/tests/test_admin_ops_migrations.py",
    ],
    "apps/backend/app/db/": [
        "app/tests/test_smoke_pg.py",
        "app/tests/test_smoke_pos_pg.py",
        "app/tests/test_tenant_isolation.py",
        "app/tests/test_pos_backfill_tenant_isolation.py",
    ],
    "apps/backend/app/config/database.py": [
        "app/tests/test_admin_ops_migrations.py",
        "app/tests/test_smoke_pg.py",
        "app/tests/test_tenant_isolation.py",
    ],
    "apps/backend/app/models/": [
        "app/tests/test_documents_persistence.py",
        "app/tests/test_inventory_costing.py",
        "app/tests/test_smoke_pg.py",
        "app/tests/test_tenant_isolation.py",
    ],
    "apps/backend/app/modules/importador/": [
        "app/tests/test_importador_async_learning.py",
        "app/tests/test_importador_tasks_learning.py",
    ],
    "apps/backend/app/modules/pos/": [
        "app/tests/test_smoke_pos_pg.py",
        "app/tests/test_pos_receipt_idempotency_pg.py",
        "app/tests/test_pos_backfill_tenant_isolation.py",
    ],
    "apps/backend/app/modules/inventory/": [
        "app/tests/test_inventory_adjust_metadata.py",
        "app/tests/test_inventory_costing.py",
        "app/tests/test_stock_transfers.py",
    ],
    "apps/backend/app/modules/production/": [
        "app/tests/test_production_business_flow.py",
    ],
}
POSTGRES_TRIGGER_PREFIXES = tuple(POSTGRES_SPECIAL_CASES.keys())
MAX_POSTGRES_SELECTED = 12


def _all_test_files() -> list[Path]:
    files: list[Path] = []
    for test_dir in TEST_DIRS:
        if test_dir.exists():
            files.extend(sorted(test_dir.rglob("test_*.py")))
    return files


ALL_TESTS = _all_test_files()
ALL_TESTS_BY_NAME: dict[str, list[Path]] = defaultdict(list)
for _path in ALL_TESTS:
    ALL_TESTS_BY_NAME[_path.name.lower()].append(_path)


def _to_backend_relative(path: Path) -> str:
    return path.relative_to(BACKEND_ROOT).as_posix()


def _git_changed_files(base_sha: str, head_sha: str) -> list[str]:
    cmd = [
        "git",
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        f"{base_sha}...{head_sha}",
    ]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _meaningful_tokens(path_str: str) -> list[str]:
    path = Path(path_str)
    tokens: list[str] = []
    for part in path.parts:
        token = part.replace(".py", "").replace("-", "_").lower().strip("_")
        if not token or token in IGNORED_TOKENS or len(token) < 3:
            continue
        tokens.append(token)
    return tokens


def _score_matches(
    changed_files: list[str],
    *,
    allowed_tests: set[str] | None = None,
    special_cases: dict[str, list[str]] | None = None,
) -> dict[str, int]:
    scores: dict[str, int] = defaultdict(int)

    def add(relative_path: str, score: int) -> None:
        full = BACKEND_ROOT / relative_path
        if full.exists() and (allowed_tests is None or relative_path in allowed_tests):
            scores[relative_path] += score

    for changed in changed_files:
        path = Path(changed)

        for prefix, tests in (special_cases or SPECIAL_CASES).items():
            if changed.startswith(prefix):
                for test in tests:
                    add(test, 100)

        if path.suffix != ".py":
            continue

        if changed.startswith("apps/backend/app/tests/") or changed.startswith("apps/backend/tests/"):
            try:
                add(_to_backend_relative(REPO_ROOT / changed), 500)
            except Exception:
                pass
            continue

        stem = path.stem.lower()
        exact_name = f"test_{stem}.py"
        for test_path in ALL_TESTS_BY_NAME.get(exact_name, []):
            add(_to_backend_relative(test_path), 250)

        if stem not in GENERIC_STEMS and len(stem) >= 4:
            for test_path in ALL_TESTS:
                test_name = test_path.name.lower()
                if stem in test_name:
                    add(_to_backend_relative(test_path), 90)

        tokens = _meaningful_tokens(changed)
        module_tokens = [t for t in tokens if t not in GENERIC_STEMS]
        for token in module_tokens:
            for test_path in ALL_TESTS:
                test_name = test_path.name.lower()
                if token in test_name:
                    add(_to_backend_relative(test_path), 25)

    return scores


def _select_tests(changed_files: list[str]) -> list[str]:
    scores = _score_matches(changed_files)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    selected = [path for path, _score in ranked[:MAX_SELECTED]]
    return selected


def _select_postgres_tests(changed_files: list[str]) -> list[str]:
    if not any(changed.startswith(POSTGRES_TRIGGER_PREFIXES) for changed in changed_files):
        # Allow direct selection if the changed file itself is already a postgres-only test.
        direct_pg_test_change = any(
            (
                changed.startswith("apps/backend/app/tests/")
                or changed.startswith("apps/backend/tests/")
            )
            and _to_backend_relative(REPO_ROOT / changed) in POSTGRES_TESTS
            for changed in changed_files
            if changed.endswith(".py")
        )
        if not direct_pg_test_change:
            return []

    scores = _score_matches(
        changed_files,
        allowed_tests=POSTGRES_TESTS,
        special_cases=POSTGRES_SPECIAL_CASES,
    )
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [path for path, _score in ranked[:MAX_POSTGRES_SELECTED]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Select backend tests related to changed files.")
    parser.add_argument("--base-sha", help="Base commit SHA for git diff")
    parser.add_argument("--head-sha", help="Head commit SHA for git diff")
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed file path relative to repo root. Can be passed multiple times.",
    )
    parser.add_argument(
        "--suite",
        choices=("related", "postgres"),
        default="related",
        help="Selection mode.",
    )
    args = parser.parse_args()

    changed_files = [f for f in args.changed_file if f]
    if not changed_files:
        if not args.base_sha or not args.head_sha:
            print("Either --changed-file or both --base-sha/--head-sha are required.", file=sys.stderr)
            return 2
        changed_files = _git_changed_files(args.base_sha, args.head_sha)

    selected = (
        _select_postgres_tests(changed_files)
        if args.suite == "postgres"
        else _select_tests(changed_files)
    )
    if args.suite == "related" and len(selected) == MAX_SELECTED:
        print(
            f"[select_backend_tests] capped selection at {MAX_SELECTED} tests",
            file=sys.stderr,
        )
    if args.suite == "postgres" and len(selected) == MAX_POSTGRES_SELECTED:
        print(
            f"[select_backend_tests] capped postgres selection at {MAX_POSTGRES_SELECTED} tests",
            file=sys.stderr,
        )

    for item in selected:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
