#!/usr/bin/env python3
# ruff: noqa: E402
"""
Generate clean SQL migrations from SQLAlchemy models.

This script:
1. Introspects all SQLAlchemy models in app/models
2. Generates a single consolidated migration with all tables
3. Creates up.sql and down.sql files
4. Places them in ops/migrations/

Usage:
    python scripts/generate_migration_from_models.py --date 2025-11-21 --number 100
    python scripts/generate_migration_from_models.py --date 2025-11-21 --number 100 --output-only  # just show SQL
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Set working directory
os.chdir(str(backend_path))

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

# Import all models to register them
try:
    # Import all models to ensure they're registered
    from app import models  # noqa
    from app.config.database import Base

    print("✅ Successfully imported all SQLAlchemy models")
except ImportError as e:
    print(f"❌ Error importing models: {e}")
    import traceback

    traceback.print_exc()
    print(
        "Make sure you're running from the project root and have all dependencies installed"
    )
    sys.exit(1)


def generate_create_table_sql() -> str:
    """Generate CREATE TABLE statements for all models."""

    # Create a temporary in-memory SQLite engine to extract schema
    # We'll use PostgreSQL dialect for better compatibility
    statements = []

    for table in Base.metadata.sorted_tables:
        # Generate CREATE TABLE statement
        create_stmt = CreateTable(table).compile(dialect=postgresql.dialect())
        sql = str(create_stmt).rstrip(";")

        # Clean up the SQL
        sql = sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
        statements.append(sql + ";")

    return "\n\n".join(statements)


def generate_drop_tables_sql() -> str:
    """Generate DROP TABLE statements in reverse order."""
    statements = []

    # Reverse order to respect foreign keys
    for table in reversed(Base.metadata.sorted_tables):
        statements.append(f"DROP TABLE IF EXISTS {table.name} CASCADE;")

    return "\n".join(statements)


def generate_up_migration(create_tables_sql: str) -> str:
    """Generate the up.sql migration."""
    return f"""-- =====================================================
-- Migration: Consolidated Schema from SQLAlchemy Models
-- Description: Create all tables from SQLAlchemy models
-- Generated: {datetime.now().isoformat()}
-- =====================================================

BEGIN;

-- =====================================================
-- Create all tables
-- =====================================================

{create_tables_sql}

-- =====================================================
-- Create indexes for common queries
-- =====================================================

-- Tenant indexes
CREATE INDEX IF NOT EXISTS idx_business_types_tenant_id ON business_types(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_categories_tenant_id ON business_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_company_categories_tenant_id ON company_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_employees_tenant_id ON employees(tenant_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_tenant_id ON suppliers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_purchases_tenant_id ON purchases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_tenant_id ON sales(tenant_id);
CREATE INDEX IF NOT EXISTS idx_expenses_tenant_id ON expenses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_warehouses_tenant_id ON warehouses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_products_tenant_id ON products(tenant_id);
CREATE INDEX IF NOT EXISTS idx_recipes_tenant_id ON recipes(tenant_id);

-- Stock management indexes
CREATE INDEX IF NOT EXISTS idx_stock_items_warehouse_id ON stock_items(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_stock_items_product_id ON stock_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_moves_stock_item_id ON stock_moves(stock_item_id);

-- POS indexes
CREATE INDEX IF NOT EXISTS idx_pos_receipts_tenant_id ON pos_receipts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pos_receipt_lines_receipt_id ON pos_receipt_lines(receipt_id);

-- Search indexes
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);

COMMIT;
"""


def generate_down_migration(drop_tables_sql: str) -> str:
    """Generate the down.sql migration."""
    return f"""-- =====================================================
-- Migration Rollback: Drop all tables
-- WARNING: This will delete ALL data
-- =====================================================

BEGIN;

{drop_tables_sql}

COMMIT;
"""


def generate_readme(table_count: int) -> str:
    """Generate README.md for the migration."""
    return f"""# Migration: Consolidated Schema from SQLAlchemy Models

## Description

This migration creates a clean, consolidated schema directly from SQLAlchemy models.
All tables are defined in a single migration with their complete schema.

## Changes

- **Tables Created**: {table_count}
- **Approach**: Single consolidated migration (not incremental)
- **Indexes**: Added for common queries (tenant_id, foreign keys, search fields)

## Table Categories

### Core
- tenants, product_categories, products

### Business Reference
- business_types, business_categories, company_categories
- currencies, countries, timezones, locales

### Inventory
- warehouses, stock_items, stock_moves, stock_alerts

### Procurement
- suppliers, supplier_contacts, supplier_addresses
- purchases, purchase_lines

### Sales & POS
- clients, sales
- pos_registers, pos_shifts, pos_receipts, pos_receipt_lines, pos_payments

### HR & Payroll
- employees, vacations
- payrolls, payroll_concepts, payroll_templates

### Finance
- cash_boxes, cash_movements, cash_box_closes
- bank_accounts, bank_transactions

### Expenses
- expenses

### Production & Recipes
- recipes, recipe_ingredients
- production_orders, production_order_lines

### E-Invoicing
- invoices, invoice_lines
- bank_accounts, bank_transactions, payments

### AI & Monitoring
- incidents, notification_channels, notification_logs

### Import System
- import_column_mappings, import_batches, import_items

## Prerequisites

- PostgreSQL 12+
- `tenants` table must exist
- Empty database (recommended)

## Application

```bash
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/*/up.sql
```

## Rollback

⚠️ **WARNING**: This will delete ALL data!

```bash
docker exec -i db psql -U postgres -d gestiqclouddb_dev < ops/migrations/*/down.sql
```

## Notes

- All tables use UUID primary keys
- Multi-tenant support via `tenant_id` column
- Audit fields: `created_at`, `updated_at`
- Proper foreign key constraints with cascading deletes
- Indexes for common queries included

---

**Status**: ✅ Ready for Application
"""


def create_migration(
    date_str: str, number: int, output_only: bool = False
) -> Optional[Path]:
    """Create migration files."""

    print("\n📊 Analyzing SQLAlchemy models...")

    # Count tables
    table_count = len(Base.metadata.sorted_tables)
    print(f"✅ Found {table_count} tables\n")

    # Generate SQL
    print("🔧 Generating SQL...")
    create_tables_sql = generate_create_table_sql()
    drop_tables_sql = generate_drop_tables_sql()

    up_content = generate_up_migration(create_tables_sql)
    down_content = generate_down_migration(drop_tables_sql)
    readme_content = generate_readme(table_count)

    if output_only:
        print("\n" + "=" * 80)
        print("UP.SQL PREVIEW:")
        print("=" * 80)
        print(up_content[:1000])
        print("\n... (truncated)")
        print("\n" + "=" * 80)
        print("DOWN.SQL PREVIEW:")
        print("=" * 80)
        print(down_content[:500])
        print("\n... (truncated)")
        return None

    # Create migration directory
    migration_name = f"{date_str}_{number:03d}_consolidated_schema_from_models"
    migration_dir = Path(__file__).parent.parent / "ops" / "migrations" / migration_name

    print(f"\n📁 Creating migration directory: {migration_dir.name}")
    migration_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    up_file = migration_dir / "up.sql"
    down_file = migration_dir / "down.sql"
    readme_file = migration_dir / "README.md"

    up_file.write_text(up_content)
    down_file.write_text(down_content)
    readme_file.write_text(readme_content)

    print(f"✅ Created {up_file.name}")
    print(f"✅ Created {down_file.name}")
    print(f"✅ Created {readme_file.name}")

    # Summary
    print("\n✅ Migration created successfully!")
    print(f"\n📍 Location: {migration_dir}")
    print(f"\n📋 Tables: {table_count}")
    print("\n🚀 Apply with:")
    print(
        f"   docker exec -i db psql -U postgres -d gestiqclouddb_dev < {migration_dir}/up.sql"
    )

    return migration_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate SQL migrations from SQLAlchemy models"
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Migration date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--number", type=int, default=100, help="Migration number (NNN)"
    )
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="Only show SQL output, don't create files",
    )

    args = parser.parse_args()

    create_migration(args.date, args.number, args.output_only)
