"""
add password_hash to usuarios_usuarioempresa (tenant users)

Revision ID: 2025_10_05_0001_add_password_hash_usuarioempresa
Revises: 
Create Date: 2025-10-05
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2025_10_05_0001_add_password_hash_usuarioempresa"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safe on Postgres: add column only if it doesn't exist
    op.execute(
        "ALTER TABLE IF EXISTS usuarios_usuarioempresa "
        "ADD COLUMN IF NOT EXISTS password_hash TEXT"
    )


def downgrade() -> None:
    # Be conservative: don't drop data automatically. If needed, uncomment next line.
    # op.execute("ALTER TABLE IF EXISTS usuarios_usuarioempresa DROP COLUMN IF EXISTS password_hash")
    pass

