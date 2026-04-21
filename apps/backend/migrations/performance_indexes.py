"""
Performance indexes for optimized database queries
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Create performance indexes for frequently queried tables"""

    # Products table indexes
    op.create_index(
        'idx_products_tenant_active',
        'products',
        ['tenant_id', 'active'],
        unique=False,
        postgresql_where=sa.text('active = true')
    )

    op.create_index(
        'idx_products_tenant_name',
        'products',
        ['tenant_id', 'name'],
        unique=False
    )

    op.create_index(
        'idx_products_tenant_category',
        'products',
        ['tenant_id', 'category_id'],
        unique=False
    )

    op.create_index(
        'idx_products_tenant_raw_material',
        'products',
        ['tenant_id', 'is_raw_material'],
        unique=False
    )

    # Stock items indexes
    op.create_index(
        'idx_stock_items_tenant_product',
        'stock_items',
        ['tenant_id', 'product_id'],
        unique=False
    )

    # Product categories indexes
    op.create_index(
        'idx_product_categories_tenant_name',
        'product_categories',
        ['tenant_id', 'name'],
        unique=False
    )

    # Company users indexes
    op.create_index(
        'idx_company_users_tenant_active',
        'company_users',
        ['tenant_id', 'is_active'],
        unique=False,
        postgresql_where=sa.text('is_active = true')
    )

    # Expenses indexes
    op.create_index(
        'idx_expenses_tenant_date',
        'expenses',
        ['tenant_id', 'date'],
        unique=False
    )

    op.create_index(
        'idx_expenses_tenant_status',
        'expenses',
        ['tenant_id', 'status'],
        unique=False
    )


def downgrade():
    """Remove performance indexes"""

    # Products table indexes
    op.drop_index('idx_products_tenant_active', table_name='products')
    op.drop_index('idx_products_tenant_name', table_name='products')
    op.drop_index('idx_products_tenant_category', table_name='products')
    op.drop_index('idx_products_tenant_raw_material', table_name='products')

    # Stock items indexes
    op.drop_index('idx_stock_items_tenant_product', table_name='stock_items')

    # Product categories indexes
    op.drop_index('idx_product_categories_tenant_name', table_name='product_categories')

    # Company users indexes
    op.drop_index('idx_company_users_tenant_active', table_name='company_users')

    # Expenses indexes
    op.drop_index('idx_expenses_tenant_date', table_name='expenses')
    op.drop_index('idx_expenses_tenant_status', table_name='expenses')
