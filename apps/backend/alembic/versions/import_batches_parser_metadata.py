"""Add parser metadata to import_batches

Revision ID: import_batches_parser_metadata
Revises: uuid_roles_002
Create Date: 2025-11-11 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "import_batches_parser_metadata"
down_revision = "uuid_roles_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_batches",
        sa.Column("parser_id", sa.String(), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("parser_choice_confidence", sa.String(), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("suggested_parser", sa.String(), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("classification_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "import_batches",
        sa.Column("ai_enhanced", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "import_batches",
        sa.Column("ai_provider", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("import_batches", "ai_provider")
    op.drop_column("import_batches", "ai_enhanced")
    op.drop_column("import_batches", "classification_confidence")
    op.drop_column("import_batches", "suggested_parser")
    op.drop_column("import_batches", "parser_choice_confidence")
    op.drop_column("import_batches", "parser_id")
