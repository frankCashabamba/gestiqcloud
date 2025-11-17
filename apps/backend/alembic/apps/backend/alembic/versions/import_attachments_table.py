"""Create import_attachments table required by the imports module.

Revision ID: import_attachments_table
Revises: import_batches_parser_metadata
Create Date: 2025-11-12 23:30:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "import_attachments_table"
down_revision = "import_batches_parser_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("import_items.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("file_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index("ix_import_attachments_tenant_id", "import_attachments", ["tenant_id"])
    op.create_index("ix_import_attachments_item_id", "import_attachments", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_import_attachments_item_id", table_name="import_attachments")
    op.drop_index("ix_import_attachments_tenant_id", table_name="import_attachments")
    op.drop_table("import_attachments")
