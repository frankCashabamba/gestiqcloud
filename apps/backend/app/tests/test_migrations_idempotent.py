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
