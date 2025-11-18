"""Fix ENUM values and UUID column defaults.

Revision ID: 004_fix_enum_and_defaults
Revises: 003_core_business_tables
Create Date: 2025-11-19 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_fix_enum_and_defaults"
down_revision = "003_core_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix ENUM values to lowercase and add UUID defaults."""
    # Drop existing sales_order_status enum with CASCADE
    op.execute("DROP TYPE IF EXISTS sales_order_status CASCADE")

    # Create corrected ENUM with lowercase values
    op.execute(
        "CREATE TYPE sales_order_status AS ENUM ('draft', 'confirmed', 'shipped', 'delivered', 'cancelled')"
    )

    # Ensure UUID columns have proper defaults
    tables_and_cols = [
        ("pos_registers", "id"),
        ("sales_orders", "id"),
        ("sales_order_items", "id"),
        ("sales", "id"),
        ("deliveries", "id"),
    ]

    for table_name, col_name in tables_and_cols:
        op.execute(
            f"ALTER TABLE IF EXISTS {table_name} ALTER COLUMN {col_name} SET DEFAULT gen_random_uuid()"
        )


def downgrade() -> None:
    """Revert ENUM and defaults."""
    # Drop corrected enum
    op.execute("DROP TYPE IF EXISTS sales_order_status CASCADE")

    # Recreate original ENUM with uppercase values
    op.execute(
        "CREATE TYPE sales_order_status AS ENUM ('DRAFT', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED')"
    )

    # Remove defaults (if we can identify them)
    tables_and_cols = [
        ("pos_registers", "id"),
        ("sales_orders", "id"),
        ("sales_order_items", "id"),
        ("sales", "id"),
        ("deliveries", "id"),
    ]

    for table_name, col_name in tables_and_cols:
        op.execute(
            f"ALTER TABLE IF EXISTS {table_name} ALTER COLUMN {col_name} DROP DEFAULT"
        )
