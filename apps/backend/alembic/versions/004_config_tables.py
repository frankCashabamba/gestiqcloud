"""Rename columns to Spanish naming convention.

Revision ID: 004_config_tables
Revises: 003_core_business_tables
Create Date: 2025-11-17 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_config_tables"
down_revision = "003_core_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename columns from English to Spanish naming convention."""

    # Rename columns in company_users table
    with op.batch_alter_table("company_users", schema=None) as batch_op:
        batch_op.alter_column("active", new_column_name="activo")
        batch_op.alter_column("is_admin", new_column_name="es_admin_empresa")

    # Rename columns in company_user_roles table
    with op.batch_alter_table("company_user_roles", schema=None) as batch_op:
        batch_op.alter_column("user_id", new_column_name="usuario_id")
        batch_op.alter_column("role_id", new_column_name="rol_id")
        batch_op.alter_column("active", new_column_name="activo")

    # Rename columns in sales table (Sale model)
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.alter_column("customer_id", new_column_name="cliente_id")
        batch_op.alter_column("date", new_column_name="fecha")
        batch_op.alter_column("status", new_column_name="estado")
        batch_op.alter_column("notes", new_column_name="notas")
        batch_op.alter_column("user_id", new_column_name="usuario_id")


def downgrade() -> None:
    """Revert columns to English naming convention."""

    # Rename columns in company_users table
    with op.batch_alter_table("company_users", schema=None) as batch_op:
        batch_op.alter_column("activo", new_column_name="active")
        batch_op.alter_column("es_admin_empresa", new_column_name="is_admin")

    # Rename columns in company_user_roles table
    with op.batch_alter_table("company_user_roles", schema=None) as batch_op:
        batch_op.alter_column("usuario_id", new_column_name="user_id")
        batch_op.alter_column("rol_id", new_column_name="role_id")
        batch_op.alter_column("activo", new_column_name="active")

    # Rename columns in sales table (Sale model)
    with op.batch_alter_table("sales", schema=None) as batch_op:
        batch_op.alter_column("cliente_id", new_column_name="customer_id")
        batch_op.alter_column("fecha", new_column_name="date")
        batch_op.alter_column("estado", new_column_name="status")
        batch_op.alter_column("notas", new_column_name="notes")
        batch_op.alter_column("usuario_id", new_column_name="user_id")
