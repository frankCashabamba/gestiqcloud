"""Create AI incident tables (incidents, notification_channels, notification_log)

Revision ID: 007_ai_incident_tables
Revises: 006_einvoicing_tables
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "007_ai_incident_tables"
down_revision = "006_einvoicing_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create incidents, notification_channels, and notification_log tables."""

    # Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("severidad", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="open"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("auto_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("ia_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ia_suggestion", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True, onupdate=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to"], ["usuarios_usuarioempresa.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_incidents_tenant_estado", "incidents", ["tenant_id", "estado"], unique=False)
    op.create_index("idx_incidents_created_at", "incidents", ["created_at"], unique=False)
    op.create_index("idx_incidents_severidad", "incidents", ["severidad"], unique=False)

    # Create notification_channels table
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True, onupdate=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notification_channels_tenant", "notification_channels", ["tenant_id"], unique=False)

    # Create notification_log table
    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stock_alert_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_alert_id"], ["stock_alerts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_notification_log_tenant", "notification_log", ["tenant_id"], unique=False)
    op.create_index("idx_notification_log_status", "notification_log", ["status"], unique=False)
    op.create_index("idx_notification_log_sent_at", "notification_log", ["sent_at"], unique=False)


def downgrade() -> None:
    """Drop incidents, notification_channels, and notification_log tables."""
    op.drop_index("idx_notification_log_sent_at", table_name="notification_log")
    op.drop_index("idx_notification_log_status", table_name="notification_log")
    op.drop_index("idx_notification_log_tenant", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("idx_notification_channels_tenant", table_name="notification_channels")
    op.drop_table("notification_channels")
    op.drop_index("idx_incidents_severidad", table_name="incidents")
    op.drop_index("idx_incidents_created_at", table_name="incidents")
    op.drop_index("idx_incidents_tenant_estado", table_name="incidents")
    op.drop_table("incidents")
