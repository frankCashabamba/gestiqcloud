"""Rename RolEmpresa fields to English.

Revision ID: 002
Revises: 001_initial_schema
Create Date: 2025-11-17

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002_rename_rolempresas_to_english"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade: rename Spanish column names to English."""
    # Rename columns in core_rolempresa table
    op.alter_column(
        "core_rolempresa",
        "nombre",
        new_column_name="name",
        existing_type=sa.String(100),
        existing_nullable=False,
    )

    op.alter_column(
        "core_rolempresa",
        "descripcion",
        new_column_name="description",
        existing_type=sa.Text(),
        existing_nullable=True,
    )

    op.alter_column(
        "core_rolempresa",
        "permisos",
        new_column_name="permissions",
        existing_type=sa.JSON(),
        existing_nullable=False,
    )

    op.alter_column(
        "core_rolempresa",
        "creado_por_empresa",
        new_column_name="created_by_company",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )

    # Drop old constraint and create new one with renamed column
    op.drop_constraint("uq_empresa_rol", "core_rolempresa", type_="unique")
    op.create_unique_constraint(
        "uq_empresa_rol",
        "core_rolempresa",
        ["tenant_id", "name"],
    )


def downgrade() -> None:
    """Downgrade: rename columns back to Spanish."""
    # Drop new constraint and create old one
    op.drop_constraint("uq_empresa_rol", "core_rolempresa", type_="unique")
    op.create_unique_constraint(
        "uq_empresa_rol",
        "core_rolempresa",
        ["tenant_id", "nombre"],
    )

    # Rename columns back
    op.alter_column(
        "core_rolempresa",
        "name",
        new_column_name="nombre",
        existing_type=sa.String(100),
        existing_nullable=False,
    )

    op.alter_column(
        "core_rolempresa",
        "description",
        new_column_name="descripcion",
        existing_type=sa.Text(),
        existing_nullable=True,
    )

    op.alter_column(
        "core_rolempresa",
        "permissions",
        new_column_name="permisos",
        existing_type=sa.JSON(),
        existing_nullable=False,
    )

    op.alter_column(
        "core_rolempresa",
        "created_by_company",
        new_column_name="creado_por_empresa",
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
