"""Convert core_rolbase PK to UUID with updated FK relationships.

Revision ID: uuid_roles_002
Revises: uuid_migration_001
Create Date: 2025-11-12 10:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "uuid_roles_002"
down_revision = "uuid_migration_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "core_rolbase",
        sa.Column(
            "id_uuid",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
    )
    op.execute("UPDATE core_rolbase SET id_uuid = gen_random_uuid() WHERE id_uuid IS NULL")

    op.add_column(
        "core_rolempresa",
        sa.Column(
            "rol_base_id_uuid",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE core_rolempresa
        SET rol_base_id_uuid = b.id_uuid
        FROM core_rolbase b
        WHERE core_rolempresa.rol_base_id::text = b.id::text
        """
    )

    op.execute(
        "ALTER TABLE core_rolempresa DROP CONSTRAINT IF EXISTS core_rolempresa_rol_base_id_fkey"
    )
    op.drop_column("core_rolempresa", "rol_base_id")
    op.alter_column("core_rolempresa", "rol_base_id_uuid", new_column_name="rol_base_id")

    op.execute("ALTER TABLE core_rolbase DROP CONSTRAINT IF EXISTS core_rolbase_pkey")
    op.drop_column("core_rolbase", "id")
    op.alter_column("core_rolbase", "id_uuid", new_column_name="id")
    op.create_primary_key("core_rolbase_pkey", "core_rolbase", ["id"])

    op.alter_column(
        "core_rolempresa",
        "rol_base_id",
        type_=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "core_rolempresa_rol_base_id_fkey",
        "core_rolempresa",
        "core_rolbase",
        ["rol_base_id"],
        ["id"],
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for core_rolbase UUID migration")
