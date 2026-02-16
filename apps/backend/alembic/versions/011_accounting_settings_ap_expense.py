"""Add AP/expense accounts to tenant_accounting_settings

Revision ID: 011_accounting_settings_ap_expense
Revises: 010_ui_configuration_tables
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "011_accounting_settings_ap_expense"
down_revision = "010_ui_configuration_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tenant_accounting_settings") as batch_op:
        batch_op.add_column(sa.Column("ap_account_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
        batch_op.add_column(
            sa.Column("vat_input_account_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("default_expense_account_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("tenant_accounting_settings") as batch_op:
        batch_op.drop_column("default_expense_account_id")
        batch_op.drop_column("vat_input_account_id")
        batch_op.drop_column("ap_account_id")

