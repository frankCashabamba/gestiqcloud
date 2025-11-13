"""RLS isolation tests for imports module.

Tests verify that:
1. Tenant A cannot see/modify tenant B's data
2. INSERT with wrong tenant_id fails
3. Queries without app.tenant_id return 0 rows (when RLS active)
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportBatch
from app.modules.imports.infrastructure.repositories import ImportsRepository
from app.modules.imports.infrastructure.tenant_middleware import set_tenant_context


@pytest.fixture
def tenant_a_id() -> uuid.UUID:
    """Tenant A UUID."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def tenant_b_id() -> uuid.UUID:
    """Tenant B UUID."""
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def setup_test_data(db: Session, tenant_a_id: uuid.UUID, tenant_b_id: uuid.UUID):
    """Create test batches for both tenants."""
    # Tenant A batches
    batch_a1 = ImportBatch(
        tenant_id=tenant_a_id,  # Legacy field
        source="test_a",
        status="PENDING",
        created_at=datetime.now(UTC),
    )
    batch_a2 = ImportBatch(
        tenant_id=tenant_a_id,
        source="test_a2",
        status="VALIDATED",
        created_at=datetime.now(UTC),
    )

    # Tenant B batches
    batch_b1 = ImportBatch(
        tenant_id=tenant_b_id,
        source="test_b",
        status="PENDING",
        created_at=datetime.now(UTC),
    )

    db.add_all([batch_a1, batch_a2, batch_b1])
    db.commit()

    yield {
        "tenant_a": {"batches": [batch_a1.id, batch_a2.id]},
        "tenant_b": {"batches": [batch_b1.id]},
    }

    # Cleanup
    db.query(ImportBatch).filter(ImportBatch.tenant_id.in_([tenant_a_id, tenant_b_id])).delete(
        synchronize_session=False
    )
    db.commit()


@pytest.mark.skipif(
    "not config.getoption('--rls')", reason="RLS tests require --rls flag and PostgreSQL DB"
)
class TestRLSIsolation:
    """RLS isolation test suite (PostgreSQL only)."""

    def test_tenant_a_cannot_see_tenant_b_data(
        self,
        db: Session,
        tenant_a_id: uuid.UUID,
        tenant_b_id: uuid.UUID,
        setup_test_data: dict,
    ):
        """Verify tenant A queries return only tenant A data."""
        repo = ImportsRepository()

        # Set context to tenant A
        set_tenant_context(db, tenant_a_id)

        batches = repo.list_batches(db, tenant_a_id)

        assert len(batches) == 2, "Tenant A should see 2 batches"
        assert all(b.tenant_id == tenant_a_id for b in batches)

        # Verify tenant B batch is not visible
        tenant_b_batch_id = setup_test_data["tenant_b"]["batches"][0]
        result = repo.get_batch(db, tenant_a_id, tenant_b_batch_id)  # noqa: F841
        assert result is None, "Tenant A should NOT see tenant B's batch"

    def test_tenant_b_cannot_see_tenant_a_data(
        self,
        db: Session,
        tenant_a_id: uuid.UUID,
        tenant_b_id: uuid.UUID,
        setup_test_data: dict,
    ):
        """Verify tenant B queries return only tenant B data."""
        repo = ImportsRepository()

        set_tenant_context(db, tenant_b_id)

        batches = repo.list_batches(db, tenant_b_id)

        assert len(batches) == 1, "Tenant B should see 1 batch"
        assert batches[0].tenant_id == tenant_b_id

    def test_insert_with_wrong_tenant_id_fails(
        self,
        db: Session,
        tenant_a_id: uuid.UUID,
        tenant_b_id: uuid.UUID,
    ):
        """Verify INSERT fails when tenant_id in data != GUC tenant_id."""
        set_tenant_context(db, tenant_a_id)

        # Try to insert batch for tenant B while context is tenant A
        bad_batch = ImportBatch(
            tenant_id=tenant_b_id,  # Mismatch!
            source="malicious",
            status="PENDING",
            created_at=datetime.now(UTC),
        )

        db.add(bad_batch)

        with pytest.raises(Exception) as exc_info:
            db.commit()

        # PostgreSQL RLS CHECK constraint violation
        assert "policy" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()
        db.rollback()

    def test_queries_without_tenant_context_return_zero_rows(
        self,
        db: Session,
        setup_test_data: dict,
    ):
        """Verify queries without SET app.tenant_id return 0 rows."""
        # Clear any existing GUC
        try:
            db.execute(text("RESET app.tenant_id"))
        except Exception:
            pass

        # Query without tenant context
        batches = db.query(ImportBatch).all()

        # With FORCE RLS, should return 0 rows
        assert len(batches) == 0, "Queries without tenant context should return 0 rows"

    def test_switching_tenant_context_changes_visible_data(
        self,
        db: Session,
        tenant_a_id: uuid.UUID,
        tenant_b_id: uuid.UUID,
        setup_test_data: dict,
    ):
        """Verify switching tenant context changes query results."""
        repo = ImportsRepository()

        # Start with tenant A
        set_tenant_context(db, tenant_a_id)
        batches_a = repo.list_batches(db, tenant_a_id)
        assert len(batches_a) == 2

        # Switch to tenant B (requires new transaction/session in practice)
        db.commit()  # End transaction to clear SET LOCAL
        db.begin()  # Start new transaction
        set_tenant_context(db, tenant_b_id)

        batches_b = repo.list_batches(db, tenant_b_id)
        assert len(batches_b) == 1
        assert batches_b[0].tenant_id == tenant_b_id


@pytest.mark.unit
class TestMiddlewareValidation:
    """Test tenant middleware without RLS (works with SQLite)."""

    def test_set_tenant_context_raises_on_none(self, db: Session):
        """Verify set_tenant_context raises ValueError for None tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be None"):
            set_tenant_context(db, None)

    def test_decorator_warns_when_tenant_id_none(self, db: Session, caplog):
        """Verify decorator logs warning when tenant_id is None."""
        repo = ImportsRepository()

        # Call with tenant_id=None (should warn but not crash)
        with caplog.at_level("WARNING"):
            batches = repo.list_batches(db, tenant_id=None)

        assert "tenant_id is None" in caplog.text
        # In SQLite (no RLS), should still return all rows
        assert isinstance(batches, list)


def pytest_addoption(parser):
    """Add --rls option to pytest."""
    parser.addoption(
        "--rls",
        action="store_true",
        default=False,
        help="Run RLS isolation tests (requires PostgreSQL)",
    )
