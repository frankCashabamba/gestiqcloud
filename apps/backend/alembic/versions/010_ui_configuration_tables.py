"""Create UI configuration tables for dynamic dashboards.

Revision ID: 010_ui_configuration_tables
Revises: 009_sector_validation_rules
Create Date: 2026-01-19 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "010_ui_configuration_tables"
down_revision = "009_sector_validation_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create UI configuration tables."""

    # Create ui_sections table
    op.create_table(
        "ui_sections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("position", sa.Integer, default=0),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column("show_in_menu", sa.Boolean, default=True),
        sa.Column("role_restrictions", postgresql.JSONB, nullable=True),
        sa.Column("module_requirement", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="ui_section_tenant_slug_unique",
        ),
        sa.Index("ix_ui_sections_tenant_id", "tenant_id"),
        sa.Index("ix_ui_sections_slug", "slug"),
        sa.Index("ix_ui_sections_active", "active"),
    )

    # Create ui_widgets table
    op.create_table(
        "ui_widgets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("widget_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("position", sa.Integer, default=0),
        sa.Column("width", sa.Integer, default=100),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("api_endpoint", sa.String(255), nullable=True),
        sa.Column("refresh_interval", sa.Integer, nullable=True),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["ui_sections.id"],
        ),
        sa.Index("ix_ui_widgets_tenant_id", "tenant_id"),
        sa.Index("ix_ui_widgets_section_id", "section_id"),
        sa.Index("ix_ui_widgets_active", "active"),
    )

    # Create ui_tables table
    op.create_table(
        "ui_tables",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("api_endpoint", sa.String(255), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("columns", postgresql.JSONB, nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=True),
        sa.Column("actions", postgresql.JSONB, nullable=True),
        sa.Column("pagination_size", sa.Integer, default=25),
        sa.Column("sortable", sa.Boolean, default=True),
        sa.Column("searchable", sa.Boolean, default=True),
        sa.Column("exportable", sa.Boolean, default=True),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="ui_table_tenant_slug_unique",
        ),
        sa.Index("ix_ui_tables_tenant_id", "tenant_id"),
        sa.Index("ix_ui_tables_slug", "slug"),
        sa.Index("ix_ui_tables_active", "active"),
    )

    # Create ui_columns table
    op.create_table(
        "ui_columns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "table_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("data_type", sa.String(50), default="string"),
        sa.Column("format", sa.String(100), nullable=True),
        sa.Column("sortable", sa.Boolean, default=True),
        sa.Column("filterable", sa.Boolean, default=True),
        sa.Column("visible", sa.Boolean, default=True),
        sa.Column("position", sa.Integer, default=0),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("align", sa.String(10), default="left"),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["ui_tables.id"],
        ),
        sa.Index("ix_ui_columns_table_id", "table_id"),
    )

    # Create ui_filters table
    op.create_table(
        "ui_filters",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "table_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("filter_type", sa.String(50), default="text"),
        sa.Column("options", postgresql.JSONB, nullable=True),
        sa.Column("default_value", sa.String(255), nullable=True),
        sa.Column("placeholder", sa.String(200), nullable=True),
        sa.Column("position", sa.Integer, default=0),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["ui_tables.id"],
        ),
        sa.Index("ix_ui_filters_table_id", "table_id"),
    )

    # Create ui_forms table
    op.create_table(
        "ui_forms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("api_endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), default="POST"),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("fields", postgresql.JSONB, nullable=False),
        sa.Column("submit_button_label", sa.String(100), default="Guardar"),
        sa.Column(
            "success_message",
            sa.String(255),
            default="Guardado exitosamente",
        ),
        sa.Column("active", sa.Boolean, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="ui_form_tenant_slug_unique",
        ),
        sa.Index("ix_ui_forms_tenant_id", "tenant_id"),
        sa.Index("ix_ui_forms_slug", "slug"),
        sa.Index("ix_ui_forms_active", "active"),
    )

    # Create ui_form_fields table
    op.create_table(
        "ui_form_fields",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "form_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("field_type", sa.String(50), default="text"),
        sa.Column("required", sa.Boolean, default=False),
        sa.Column("validation", postgresql.JSONB, nullable=True),
        sa.Column("options", postgresql.JSONB, nullable=True),
        sa.Column("placeholder", sa.String(200), nullable=True),
        sa.Column("help_text", sa.String(255), nullable=True),
        sa.Column("position", sa.Integer, default=0),
        sa.Column("default_value", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["form_id"],
            ["ui_forms.id"],
        ),
        sa.Index("ix_ui_form_fields_form_id", "form_id"),
    )

    # Create ui_dashboards table
    op.create_table(
        "ui_dashboards",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("sections", postgresql.JSONB, nullable=False),
        sa.Column("is_default", sa.Boolean, default=False),
        sa.Column("role_visibility", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="ui_dashboard_tenant_slug_unique",
        ),
        sa.Index("ix_ui_dashboards_tenant_id", "tenant_id"),
        sa.Index("ix_ui_dashboards_slug", "slug"),
    )


def downgrade() -> None:
    """Drop UI configuration tables."""
    op.drop_table("ui_dashboards")
    op.drop_table("ui_form_fields")
    op.drop_table("ui_forms")
    op.drop_table("ui_filters")
    op.drop_table("ui_columns")
    op.drop_table("ui_tables")
    op.drop_table("ui_widgets")
    op.drop_table("ui_sections")
