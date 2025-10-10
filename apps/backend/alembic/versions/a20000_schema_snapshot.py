"""
Schema snapshot after ops SQL migrations.

This revision marks the current DB state as baseline for future Alembic-only
changes. It intentionally performs no DDL.

Revision ID: a20000_schema_snapshot
Revises: a10001_pwdhash_empuser
Create Date: 2025-10-10
"""

from alembic import op  # noqa: F401  (kept for consistency)


# revision identifiers, used by Alembic.
revision = "a20000_schema_snapshot"
down_revision = "a10001_pwdhash_empuser"
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - no-op by design
    # No-op: schema is already at desired state due to prior ops SQL migrations.
    # Future changes should be added in Alembic revisions after this one.
    pass


def downgrade() -> None:  # pragma: no cover - no-op by design
    # No-op: we don't attempt to roll back the snapshot.
    pass

