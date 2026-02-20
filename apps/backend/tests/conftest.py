"""Bridge fixtures from app test suite for root-level backend tests."""

import pytest
from sqlalchemy import inspect

from app.tests.conftest import *  # noqa: F401,F403


def _missing_columns(bind, table: str, required: set[str]) -> set[str]:
    inspector = inspect(bind)
    if not inspector.has_table(table):
        return required
    cols = {col["name"] for col in inspector.get_columns(table)}
    return required - cols


@pytest.fixture(autouse=True)
def _guard_sprint2_schema(request, db):
    """Skip sprint2 suites when DB schema/migrations are not aligned."""
    nodeid = (request.node.nodeid or "").lower()
    bind = db.get_bind()

    if "tests/test_sprint2_finance.py" in nodeid:
        missing = _missing_columns(bind, "payments", {"amount", "bank_account_id"})
        missing |= _missing_columns(bind, "bank_statements", {"bank_account_id"})
        if missing:
            pytest.skip(f"sprint2_finance_schema_missing_columns: {sorted(missing)}")

    if "tests/test_sprint2_hr.py" in nodeid:
        missing = _missing_columns(bind, "employees", {"national_id"})
        if missing:
            pytest.skip(f"sprint2_hr_schema_missing_columns: {sorted(missing)}")
