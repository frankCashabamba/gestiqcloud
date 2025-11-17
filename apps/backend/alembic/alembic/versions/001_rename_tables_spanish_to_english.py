"""Rename Spanish table names to English - Phase 1: Core enums and catalogs.

Revision ID: spanish_to_english_001
Revises: merge_imports_roles
Create Date: 2025-11-17 12:00:00.000000

Tables renamed:
- core_tipoempresa -> business_types
- core_tiponegocio -> business_categories
- core_moneda -> currencies (legacy, keep for now, sync with currencies table)
- core_dia -> weekdays
- core_horarioatencion -> business_hours
- auditoria_importacion -> import_audits
"""

from alembic import op

revision = "spanish_to_english_001"
down_revision = "merge_imports_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename core enum/catalog tables from Spanish to English."""

    # 1. Rename core_tipoempresa -> business_types
    op.rename_table("core_tipoempresa", "business_types")

    # 2. Rename core_tiponegocio -> business_categories
    op.rename_table("core_tiponegocio", "business_categories")

    # 3. Rename core_dia -> weekdays
    op.rename_table("core_dia", "weekdays")

    # 4. Update foreign key in core_horarioatencion before renaming
    with op.batch_alter_table("core_horarioatencion", schema=None) as batch_op:
        batch_op.alter_column("dia_id", new_column_name="weekday_id")

    # Drop and recreate FK to use new table name
    with op.batch_alter_table("core_horarioatencion", schema=None) as batch_op:
        batch_op.drop_constraint("core_horarioatencion_dia_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "core_horarioatencion_weekday_id_fkey", "weekdays", ["weekday_id"], ["id"]
        )

    # 5. Rename core_horarioatencion -> business_hours
    op.rename_table("core_horarioatencion", "business_hours")

    # Rename columns in business_hours
    with op.batch_alter_table("business_hours", schema=None) as batch_op:
        batch_op.alter_column("inicio", new_column_name="start_time")
        batch_op.alter_column("fin", new_column_name="end_time")

    # Rename columns in weekdays
    with op.batch_alter_table("weekdays", schema=None) as batch_op:
        batch_op.alter_column("clave", new_column_name="key")
        batch_op.alter_column("nombre", new_column_name="name")
        batch_op.alter_column("orden", new_column_name="order")

    # 6. Rename auditoria_importacion -> import_audits
    op.rename_table("auditoria_importacion", "import_audits")

    # Rename columns in import_audits
    with op.batch_alter_table("import_audits", schema=None) as batch_op:
        batch_op.alter_column("documento_id", new_column_name="document_id")
        batch_op.alter_column("usuario_id", new_column_name="user_id")
        batch_op.alter_column("fecha", new_column_name="created_at")

    # Update FK in import_audits
    with op.batch_alter_table("import_audits", schema=None) as batch_op:
        batch_op.drop_constraint("auditoria_importacion_usuario_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "import_audits_user_id_fkey", "usuarios_usuarioempresa", ["user_id"], ["id"]
        )

    # Update FK in core_sectorplantilla
    with op.batch_alter_table("core_sectorplantilla", schema=None) as batch_op:
        batch_op.drop_constraint("core_sectorplantilla_business_type_id_fkey", type_="foreignkey")
        batch_op.drop_constraint(
            "core_sectorplantilla_business_category_id_fkey", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "core_sectorplantilla_business_type_id_fkey",
            "business_types",
            ["business_type_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "core_sectorplantilla_business_category_id_fkey",
            "business_categories",
            ["business_category_id"],
            ["id"],
        )


def downgrade() -> None:
    """Reverse table renames."""

    # Revert core_sectorplantilla FKs
    with op.batch_alter_table("core_sectorplantilla", schema=None) as batch_op:
        batch_op.drop_constraint("core_sectorplantilla_business_type_id_fkey", type_="foreignkey")
        batch_op.drop_constraint(
            "core_sectorplantilla_business_category_id_fkey", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "core_sectorplantilla_business_type_id_fkey",
            "core_tipoempresa",
            ["business_type_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "core_sectorplantilla_business_category_id_fkey",
            "core_tiponegocio",
            ["business_category_id"],
            ["id"],
        )

    # Revert import_audits
    with op.batch_alter_table("import_audits", schema=None) as batch_op:
        batch_op.drop_constraint("import_audits_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "auditoria_importacion_usuario_id_fkey", "usuarios_usuarioempresa", ["user_id"], ["id"]
        )
        batch_op.alter_column("created_at", new_column_name="fecha")
        batch_op.alter_column("user_id", new_column_name="usuario_id")
        batch_op.alter_column("document_id", new_column_name="documento_id")

    op.rename_table("import_audits", "auditoria_importacion")

    # Revert business_hours
    with op.batch_alter_table("business_hours", schema=None) as batch_op:
        batch_op.alter_column("start_time", new_column_name="inicio")
        batch_op.alter_column("end_time", new_column_name="fin")
        batch_op.drop_constraint("core_horarioatencion_weekday_id_fkey", type_="foreignkey")
        batch_op.alter_column("weekday_id", new_column_name="dia_id")
        batch_op.create_foreign_key(
            "core_horarioatencion_dia_id_fkey", "core_dia", ["dia_id"], ["id"]
        )

    op.rename_table("business_hours", "core_horarioatencion")

    # Revert weekdays
    with op.batch_alter_table("weekdays", schema=None) as batch_op:
        batch_op.alter_column("order", new_column_name="orden")
        batch_op.alter_column("name", new_column_name="nombre")
        batch_op.alter_column("key", new_column_name="clave")

    op.rename_table("weekdays", "core_dia")
    op.rename_table("business_categories", "core_tiponegocio")
    op.rename_table("business_types", "core_tipoempresa")
