"""Create e-invoicing tables (einv_credentials, sri_submissions, sii_batches, sii_batch_items)

Revision ID: 006_einvoicing_tables
Revises: 005_pos_extensions
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "006_einvoicing_tables"
down_revision = "005_pos_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create e-invoicing tables."""

    # Create ENUM types
    op.execute(
        """
        CREATE TYPE sri_status AS ENUM (
            'PENDING', 'SENT', 'RECEIVED', 'AUTHORIZED', 'REJECTED', 'ERROR'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE sii_batch_status AS ENUM (
            'PENDING', 'SENT', 'ACCEPTED', 'PARTIAL', 'REJECTED', 'ERROR'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE sii_item_status AS ENUM (
            'PENDING', 'SENT', 'ACCEPTED', 'REJECTED', 'ERROR'
        )
        """
    )

    # Create einv_credentials table
    op.create_table(
        "einv_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("sri_cert_ref", sa.Text(), nullable=True),
        sa.Column("sri_key_ref", sa.Text(), nullable=True),
        sa.Column("sri_env", sa.String(20), nullable=True),
        sa.Column("sii_agency", sa.Text(), nullable=True),
        sa.Column("sii_cert_ref", sa.Text(), nullable=True),
        sa.Column("sii_key_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_einv_credentials_tenant_id"), "einv_credentials", ["tenant_id"], unique=False)

    # Create sri_submissions table
    op.create_table(
        "sri_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum(
            'PENDING', 'SENT', 'RECEIVED', 'AUTHORIZED', 'REJECTED', 'ERROR',
            name='sri_status'
        ), nullable=False, server_default="PENDING"),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("receipt_number", sa.Text(), nullable=True),
        sa.Column("authorization_number", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sri_submissions_tenant_id"), "sri_submissions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sri_submissions_invoice_id"), "sri_submissions", ["invoice_id"], unique=False)

    # Create sii_batches table
    op.create_table(
        "sii_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("status", sa.Enum(
            'PENDING', 'SENT', 'ACCEPTED', 'PARTIAL', 'REJECTED', 'ERROR',
            name='sii_batch_status'
        ), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sii_batches_tenant_id"), "sii_batches", ["tenant_id"], unique=False)

    # Create sii_batch_items table
    op.create_table(
        "sii_batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Enum(
            'PENDING', 'SENT', 'ACCEPTED', 'REJECTED', 'ERROR',
            name='sii_item_status'
        ), nullable=False, server_default="PENDING"),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["batch_id"], ["sii_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sii_batch_items_tenant_id"), "sii_batch_items", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_sii_batch_items_batch_id"), "sii_batch_items", ["batch_id"], unique=False)


def downgrade() -> None:
    """Drop e-invoicing tables."""
    op.drop_index(op.f("ix_sii_batch_items_batch_id"), table_name="sii_batch_items")
    op.drop_index(op.f("ix_sii_batch_items_tenant_id"), table_name="sii_batch_items")
    op.drop_table("sii_batch_items")
    op.drop_index(op.f("ix_sii_batches_tenant_id"), table_name="sii_batches")
    op.drop_table("sii_batches")
    op.drop_index(op.f("ix_sri_submissions_invoice_id"), table_name="sri_submissions")
    op.drop_index(op.f("ix_sri_submissions_tenant_id"), table_name="sri_submissions")
    op.drop_table("sri_submissions")
    op.drop_index(op.f("ix_einv_credentials_tenant_id"), table_name="einv_credentials")
    op.drop_table("einv_credentials")

    # Drop ENUM types
    op.execute("DROP TYPE sii_item_status")
    op.execute("DROP TYPE sii_batch_status")
    op.execute("DROP TYPE sri_status")
