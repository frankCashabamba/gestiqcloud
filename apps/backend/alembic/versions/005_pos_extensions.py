"""Create POS extension tables (store_credits, store_credit_events)

Revision ID: 005_pos_extensions
Revises: 004_config_tables
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_pos_extensions"
down_revision = "004_config_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create store_credits and store_credit_events tables."""

    # Create store_credits table
    op.create_table(
        "store_credits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_initial", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_remaining", sa.Numeric(12, 2), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["clients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_store_credits_id"), "store_credits", ["id"], unique=False)
    op.create_index(op.f("ix_store_credits_tenant_id"), "store_credits", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_store_credits_code"), "store_credits", ["code"], unique=True)

    # Create store_credit_events table
    op.create_table(
        "store_credit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("credit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("ref_doc_type", sa.String(50), nullable=True),
        sa.Column("ref_doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["credit_id"], ["store_credits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_store_credit_events_credit_id"), "store_credit_events", ["credit_id"], unique=False)


def downgrade() -> None:
    """Drop store_credits and store_credit_events tables."""
    op.drop_index(op.f("ix_store_credit_events_credit_id"), table_name="store_credit_events")
    op.drop_table("store_credit_events")
    op.drop_index(op.f("ix_store_credits_code"), table_name="store_credits")
    op.drop_index(op.f("ix_store_credits_tenant_id"), table_name="store_credits")
    op.drop_index(op.f("ix_store_credits_id"), table_name="store_credits")
    op.drop_table("store_credits")
