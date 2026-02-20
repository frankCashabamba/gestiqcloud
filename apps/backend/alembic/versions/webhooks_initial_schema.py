"""Webhooks initial schema.

Revision ID: webhooks_001
Revises: (previous migration)
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'webhooks_001'
down_revision = None  # Set to previous migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_subscriptions table
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('target_url', sa.String(2048), nullable=False),
        sa.Column('secret', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_delivery_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_subscriptions_tenant_id', 'webhook_subscriptions', ['tenant_id'])
    op.create_index('ix_webhook_subscriptions_event_type', 'webhook_subscriptions', ['event_type'])
    op.create_index('ix_webhook_subscriptions_is_active', 'webhook_subscriptions', ['is_active'])

    # Create webhook_deliveries table
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('payload', postgresql.JSON(none_as_null=True), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('error_message', sa.String(1024), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_webhook_deliveries_subscription_id', 'webhook_deliveries', ['subscription_id'])
    op.create_index('ix_webhook_deliveries_event_type', 'webhook_deliveries', ['event_type'])
    op.create_index('ix_webhook_deliveries_next_retry_at', 'webhook_deliveries', ['next_retry_at'])
    op.create_index('ix_webhook_deliveries_created_at', 'webhook_deliveries', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_webhook_deliveries_created_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_next_retry_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_event_type', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_subscription_id', table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')
    
    op.drop_index('ix_webhook_subscriptions_is_active', table_name='webhook_subscriptions')
    op.drop_index('ix_webhook_subscriptions_event_type', table_name='webhook_subscriptions')
    op.drop_index('ix_webhook_subscriptions_tenant_id', table_name='webhook_subscriptions')
    op.drop_table('webhook_subscriptions')
