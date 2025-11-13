"""Merge import batches metadata and role UUID migrations.

Revision ID: merge_imports_roles
Revises: import_batches_parser_metadata, uuid_roles_002
Create Date: 2025-11-12 20:10:00.000000
"""

# revision identifiers, used by Alembic.
revision = "merge_imports_roles"
down_revision = ("import_batches_parser_metadata", "uuid_roles_002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
