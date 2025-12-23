"""Create sector_validation_rules table.

Revision ID: 009_sector_validation_rules
Revises: 008_fix_enum_and_defaults
Create Date: 2025-12-01 00:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "009_sector_validation_rules"
down_revision = "008_fix_enum_and_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create sector_validation_rules table."""
    op.create_table(
        "sector_validation_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
            default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "sector_template_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "context",
            sa.String(50),
            nullable=False,
            comment="'product', 'inventory', 'sale', 'customer'",
        ),
        sa.Column(
            "field",
            sa.String(100),
            nullable=False,
            comment="The field being validated",
        ),
        sa.Column(
            "rule_type",
            sa.String(50),
            nullable=False,
            comment="'required', 'min_value', 'max_value', 'pattern', 'custom'",
        ),
        sa.Column(
            "condition",
            postgresql.JSON(),
            nullable=False,
            comment="Condition logic as JSON",
        ),
        sa.Column(
            "message",
            sa.String(500),
            nullable=False,
            comment="Error/warning message",
        ),
        sa.Column(
            "level",
            sa.String(20),
            nullable=False,
            server_default="error",
            comment="'error', 'warning'",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="Execution order",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["sector_template_id"],
            ["sector_templates.id"],
            name="fk_sector_validation_rules_sector_template",
        ),
        sa.PrimaryKeyConstraint("id"),
        extend_existing=True,
    )
    op.create_index(
        "ix_sector_validation_rules_sector_template_id",
        "sector_validation_rules",
        ["sector_template_id"],
    )
    op.create_index(
        "ix_sector_validation_rules_context",
        "sector_validation_rules",
        ["context"],
    )


def downgrade() -> None:
    """Drop sector_validation_rules table."""
    op.drop_index(
        "ix_sector_validation_rules_context",
        table_name="sector_validation_rules",
    )
    op.drop_index(
        "ix_sector_validation_rules_sector_template_id",
        table_name="sector_validation_rules",
    )
    op.drop_table("sector_validation_rules")
