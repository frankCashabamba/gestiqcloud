"""Create bank_statements and statement_lines tables

Revision ID: 014_reconciliation_tables
Revises: 013_notifications_tables
Create Date: 2025-02-16 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "014_reconciliation_tables"
down_revision = "013_notifications_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create reconciliation tables."""

    # Create bank_statements table
    op.create_table(
        "bank_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bank_name", sa.String(200), nullable=False),
        sa.Column("account_number", sa.String(50), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column(
            "import_format",
            sa.String(20),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="imported",
        ),
        sa.Column(
            "total_transactions",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "matched_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "unmatched_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
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
        "idx_bank_statements_tenant_id",
        "bank_statements",
        ["tenant_id"],
        schema="public",
    )

    op.create_index(
        "idx_bank_statements_tenant_date",
        "bank_statements",
        ["tenant_id", "statement_date"],
        schema="public",
    )

    # Create statement_lines table
    op.create_table(
        "statement_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "statement_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("balance", sa.Numeric(15, 2), nullable=True),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column(
            "matched_invoice_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "match_status",
            sa.String(20),
            nullable=False,
            server_default="unmatched",
        ),
        sa.Column("match_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["bank_statements.id"],
            ondelete="CASCADE",
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
        "idx_statement_lines_statement_id",
        "statement_lines",
        ["statement_id"],
        schema="public",
    )

    op.create_index(
        "idx_statement_lines_tenant_id",
        "statement_lines",
        ["tenant_id"],
        schema="public",
    )

    op.create_index(
        "idx_statement_lines_match_status",
        "statement_lines",
        ["tenant_id", "match_status"],
        schema="public",
    )

    # Enable RLS on both tables
    op.execute("ALTER TABLE bank_statements ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE statement_lines ENABLE ROW LEVEL SECURITY;")

    # Create RLS policies
    op.execute(
        """
        CREATE POLICY bank_statements_tenant_policy
        ON bank_statements
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )

    op.execute(
        """
        CREATE POLICY statement_lines_tenant_policy
        ON statement_lines
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    """Drop reconciliation tables."""

    # Drop policies
    op.execute(
        "DROP POLICY IF EXISTS bank_statements_tenant_policy ON bank_statements;"
    )
    op.execute(
        "DROP POLICY IF EXISTS statement_lines_tenant_policy ON statement_lines;"
    )

    # Disable RLS
    op.execute("ALTER TABLE bank_statements DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE statement_lines DISABLE ROW LEVEL SECURITY;")

    # Drop indices
    op.drop_index(
        "idx_statement_lines_match_status",
        schema="public",
        table_name="statement_lines",
    )
    op.drop_index(
        "idx_statement_lines_tenant_id",
        schema="public",
        table_name="statement_lines",
    )
    op.drop_index(
        "idx_statement_lines_statement_id",
        schema="public",
        table_name="statement_lines",
    )
    op.drop_index(
        "idx_bank_statements_tenant_date",
        schema="public",
        table_name="bank_statements",
    )
    op.drop_index(
        "idx_bank_statements_tenant_id",
        schema="public",
        table_name="bank_statements",
    )

    # Drop tables (order matters: lines first due to FK)
    op.drop_table("statement_lines", schema="public")
    op.drop_table("bank_statements", schema="public")
