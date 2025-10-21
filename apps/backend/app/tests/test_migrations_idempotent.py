from __future__ import annotations

from pathlib import Path


def _find_ops_root(start: Path) -> Path:
    cur = start
    for _ in range(6):
        candidate = cur / "ops" / "migrations"
        if candidate.exists():
            return cur
        cur = cur.parent
    raise AssertionError("Could not locate ops/migrations from test path")


def test_baseline_enum_creation_is_idempotent():
    # Locate repo root robustly from this test file (apps/backend/app/tests/...)
    here = Path(__file__).resolve()
    root = _find_ops_root(here)
    sql_path = root / "ops" / "migrations" / "2025-09-22_000_baseline_full_schema" / "up.sql"
    assert sql_path.exists(), f"Missing migration file: {sql_path}"
    content = sql_path.read_text(encoding="utf-8")
    assert "typname = 'movimientoestado'" in content
    assert "typname = 'movimientotipo'" in content
    assert "IF NOT EXISTS" in content


def test_fix_missing_id_defaults_migration_present():
    """
    Ensure the generic migration that restores auto-increment defaults on
    integer PK 'id' columns exists and contains expected guards/actions.
    This is a static check (filesystem), not a runtime DB assertion
    because tests run on SQLite.
    """
    here = Path(__file__).resolve()
    root = _find_ops_root(here)
    mig_dir = root / "ops" / "migrations" / "2025-10-20_134_fix_missing_id_defaults_all"
    up_sql = mig_dir / "up.sql"
    assert up_sql.exists(), f"Missing migration file: {up_sql}"
    sql = up_sql.read_text(encoding="utf-8")
    # Should scan information_schema and primary keys
    assert "information_schema" in sql and "PRIMARY KEY" in sql
    # Should create sequence if missing and set DEFAULT nextval
    assert "CREATE SEQUENCE IF NOT EXISTS" in sql
    assert "ALTER TABLE" in sql and "SET DEFAULT nextval" in sql
