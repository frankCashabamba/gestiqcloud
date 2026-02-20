"""Create webhook subscriptions and deliveries tables

Revision ID: 012_webhook_subscriptions
Revises: 011_accounting_settings_ap_expense
Create Date: 2024-02-14 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_webhook_subscriptions"
down_revision = "011_accounting_settings_ap_expense"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create webhook tables for subscriptions and deliveries"""

    # Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
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

    # Create index on tenant_id and event for performance
    op.create_index(
        "idx_webhook_subscriptions_tenant_event",
        "webhook_subscriptions",
        ["tenant_id", "event"],
        schema="public",
    )

    # Create index on active for filtering
    op.create_index(
        "idx_webhook_subscriptions_active",
        "webhook_subscriptions",
        ["active"],
        schema="public",
    )

    # Create webhook_deliveries table
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("target_url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
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

    # Create indices for deliveries
    op.create_index(
        "idx_webhook_deliveries_tenant_status",
        "webhook_deliveries",
        ["tenant_id", "status"],
        schema="public",
    )

    op.create_index(
        "idx_webhook_deliveries_tenant_event",
        "webhook_deliveries",
        ["tenant_id", "event"],
        schema="public",
    )

    op.create_index(
        "idx_webhook_deliveries_status",
        "webhook_deliveries",
        ["status"],
        schema="public",
    )

    # Enable RLS on both tables
    op.execute("ALTER TABLE webhook_subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;")

    # Create RLS policies for subscriptions
    op.execute(
        """
        CREATE POLICY webhook_subscriptions_tenant_policy
        ON webhook_subscriptions
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )

    # Create RLS policies for deliveries
    op.execute(
        """
        CREATE POLICY webhook_deliveries_tenant_policy
        ON webhook_deliveries
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    """Drop webhook tables"""

    # Drop policies
    op.execute("DROP POLICY IF EXISTS webhook_subscriptions_tenant_policy ON webhook_subscriptions;")
    op.execute("DROP POLICY IF EXISTS webhook_deliveries_tenant_policy ON webhook_deliveries;")

    # Disable RLS
    op.execute("ALTER TABLE webhook_subscriptions DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE webhook_deliveries DISABLE ROW LEVEL SECURITY;")

    # Drop indices
    op.drop_index(
        "idx_webhook_subscriptions_active",
        schema="public",
        table_name="webhook_subscriptions",
    )
    op.drop_index(
        "idx_webhook_subscriptions_tenant_event",
        schema="public",
        table_name="webhook_subscriptions",
    )
    op.drop_index(
        "idx_webhook_deliveries_status",
        schema="public",
        table_name="webhook_deliveries",
    )
    op.drop_index(
        "idx_webhook_deliveries_tenant_event",
        schema="public",
        table_name="webhook_deliveries",
    )
    op.drop_index(
        "idx_webhook_deliveries_tenant_status",
        schema="public",
        table_name="webhook_deliveries",
    )

    # Drop tables
    op.drop_table("webhook_deliveries", schema="public")
    op.drop_table("webhook_subscriptions", schema="public")
