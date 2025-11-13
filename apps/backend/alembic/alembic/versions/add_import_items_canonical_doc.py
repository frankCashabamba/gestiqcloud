"""Add canonical_doc column to import_items

Revision ID: import_items_canonical_doc
Revises: import_batches_parser_metadata
Create Date: 2025-11-13 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "import_items_canonical_doc"
down_revision = "import_batches_parser_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_items",
        sa.Column(
            "canonical_doc",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("import_items", "canonical_doc")
