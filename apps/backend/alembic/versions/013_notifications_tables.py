"""Create notifications and notification_templates tables

Revision ID: 013_notifications_tables
Revises: 012_webhook_subscriptions
Create Date: 2024-03-01 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "013_notifications_tables"
down_revision = "012_webhook_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create notification tables."""

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
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

    # Indices for notifications
    op.create_index(
        "idx_notifications_tenant_id",
        "notifications",
        ["tenant_id"],
        schema="public",
    )
    op.create_index(
        "idx_notifications_user_id",
        "notifications",
        ["user_id"],
        schema="public",
    )
    op.create_index(
        "idx_notifications_tenant_user",
        "notifications",
        ["tenant_id", "user_id"],
        schema="public",
    )
    op.create_index(
        "idx_notifications_status",
        "notifications",
        ["status"],
        schema="public",
    )

    # Create notification_templates table
    op.create_table(
        "notification_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("tenant_id", "name", name="uq_notification_template_tenant_name"),
        schema="public",
    )

    # Index for templates
    op.create_index(
        "idx_notification_templates_tenant_id",
        "notification_templates",
        ["tenant_id"],
        schema="public",
    )

    # Enable RLS on both tables
    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;")

    # RLS policies for notifications
    op.execute(
        """
        CREATE POLICY notifications_tenant_policy
        ON notifications
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )

    # RLS policies for notification_templates
    op.execute(
        """
        CREATE POLICY notification_templates_tenant_policy
        ON notification_templates
        USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    """Drop notification tables."""

    # Drop policies
    op.execute("DROP POLICY IF EXISTS notifications_tenant_policy ON notifications;")
    op.execute("DROP POLICY IF EXISTS notification_templates_tenant_policy ON notification_templates;")

    # Disable RLS
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE notification_templates DISABLE ROW LEVEL SECURITY;")

    # Drop indices
    op.drop_index("idx_notification_templates_tenant_id", schema="public", table_name="notification_templates")
    op.drop_index("idx_notifications_status", schema="public", table_name="notifications")
    op.drop_index("idx_notifications_tenant_user", schema="public", table_name="notifications")
    op.drop_index("idx_notifications_user_id", schema="public", table_name="notifications")
    op.drop_index("idx_notifications_tenant_id", schema="public", table_name="notifications")

    # Drop tables
    op.drop_table("notification_templates", schema="public")
    op.drop_table("notifications", schema="public")
