"""
Create admin_migration_runs table to persist migration run history

Revision ID: a20006_admin_migration_runs
Revises: a20005_tenants_bootstrap
Create Date: 2025-10-10
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a20006_admin_migration_runs"
down_revision = "a20005_tenants_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:  # pragma: no cover - DDL heavy
    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE TABLE IF NOT EXISTS public.admin_migration_runs (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          started_at timestamptz NOT NULL DEFAULT now(),
          finished_at timestamptz,
          mode text NOT NULL,
          ok boolean,
          error text,
          job_id text,
          pending_count integer,
          revisions jsonb,
          triggered_by text
        );
        CREATE INDEX IF NOT EXISTS ix_admin_migration_runs_started ON public.admin_migration_runs (started_at DESC);
        """
    )


def downgrade() -> None:  # pragma: no cover - keep history by default
    pass

