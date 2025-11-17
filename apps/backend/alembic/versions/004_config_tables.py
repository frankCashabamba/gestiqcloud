"""Create config tables (doc_series, base_roles)

Revision ID: 004_config_tables
Revises: 003_core_business_tables
Create Date: 2025-11-17 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_config_tables"
down_revision = "003_core_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create doc_series and base_roles tables."""

    # Create base_roles table
    op.create_table(
        "base_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create doc_series table
    op.create_table(
        "doc_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("register_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doc_type", sa.String(10), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("current_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reset_policy", sa.String(20), nullable=False, server_default="yearly"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["register_id"], ["pos_registers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_doc_series_id"), "doc_series", ["id"], unique=False)
    op.create_index(op.f("ix_doc_series_tenant_id"), "doc_series", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_doc_series_register_id"), "doc_series", ["register_id"], unique=False)


def downgrade() -> None:
    """Drop doc_series and base_roles tables."""
    op.drop_index(op.f("ix_doc_series_register_id"), table_name="doc_series")
    op.drop_index(op.f("ix_doc_series_tenant_id"), table_name="doc_series")
    op.drop_index(op.f("ix_doc_series_id"), table_name="doc_series")
    op.drop_table("doc_series")
    op.drop_table("base_roles")
