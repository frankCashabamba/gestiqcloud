"""Create reports and scheduled_reports tables

Revision ID: 015_reports_tables
Revises: 014_reconciliation_tables
Create Date: 2025-02-16 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "015_reports_tables"
down_revision = "014_reconciliation_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create reports and scheduled_reports tables."""

    # reports table
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ready"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["empresas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )

    op.create_index(
        "idx_reports_tenant_id",
        "reports",
        ["tenant_id"],
        schema="public",
    )

    # scheduled_reports table
    op.create_table(
        "scheduled_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("recipients", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_generated_at", sa.DateTime(), nullable=True),
        sa.Column("next_scheduled_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["empresas.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )

    op.create_index(
        "idx_scheduled_reports_tenant_id",
        "scheduled_reports",
        ["tenant_id"],
        schema="public",
    )

    # Enable RLS
    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;")

    # RLS policies
    op.execute(
        """
        CREATE POLICY reports_tenant_policy
        ON reports
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )

    op.execute(
        """
        CREATE POLICY scheduled_reports_tenant_policy
        ON scheduled_reports
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    """Drop reports and scheduled_reports tables."""

    # Drop policies
    op.execute("DROP POLICY IF EXISTS reports_tenant_policy ON reports;")
    op.execute("DROP POLICY IF EXISTS scheduled_reports_tenant_policy ON scheduled_reports;")

    # Disable RLS
    op.execute("ALTER TABLE reports DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE scheduled_reports DISABLE ROW LEVEL SECURITY;")

    # Drop indices
    op.drop_index("idx_scheduled_reports_tenant_id", schema="public", table_name="scheduled_reports")
    op.drop_index("idx_reports_tenant_id", schema="public", table_name="reports")

    # Drop tables
    op.drop_table("scheduled_reports", schema="public")
    op.drop_table("reports", schema="public")
