# Migration: Complete Consolidated Schema

## Description

This is a professional, complete schema migration that consolidates all SQLAlchemy models into a single migration.

**Key characteristics**:
- [OK] Single consolidated migration (not fragmented)
- [OK] Clean database start (drops all tables first)
- [OK] All 74 tables created with complete schema
- [OK] Proper indexes for performance
- [OK] Multi-tenant support (tenant_id on all relevant tables)
- [OK] Modern PostgreSQL features (UUIDs, JSONB, etc.)

## What's Included

### Core Tables
- `tenants` - Multi-tenant configuration
- `products`, `product_categories` - Product catalog
- `clients` - Client management

### Inventory
- `warehouses`, `stock_items`, `stock_moves`, `stock_alerts`

### Sales & POS
- `sales` - Sales orders
- `pos_registers`, `pos_shifts`, `pos_receipts`, `pos_receipt_lines`, `pos_payments`
- `doc_series` - Document numbering series

### Procurement
- `suppliers`, `supplier_contacts`, `supplier_addresses`
- `purchases`, `purchase_lines`

### Expenses & Finance
- `expenses`
- `cash_boxes`, `cash_movements`, `cash_box_closes`
- `bank_accounts`, `bank_transactions`, `bank_movements`, `internal_transfers`

### HR & Payroll
- `employees`, `vacations`
- `payrolls`, `payroll_concepts`, `payroll_templates`

### Production & Manufacturing
- `recipes`, `recipe_ingredients`
- `production_orders`, `production_order_lines`

### E-Invoicing
- `invoices`, `invoices_temp`, `invoice_lines`
- `payments`

### Configuration & Reference
- `modules`, `company_modules`, `assigned_modules`
- `business_types`, `business_categories`, `company_categories`, `sector_templates`
- `currencies`, `countries`, `languages`, `ref_timezones`, `ref_locales`
- `company_roles`, `company_users`, `company_user_roles`, `user_profiles`
- `company_settings`, `inventory_settings`, `tenant_settings`

### AI & Monitoring
- `incidents`, `notification_channels`, `notification_logs`

### Import System
- `import_column_mappings`, `import_audits`

### Auth & Security
- `auth_audits`, `refresh_families`

## Features

[OK] **Performance**:
- Indexes on `tenant_id` (multi-tenancy)
- Indexes on foreign keys (join performance)
- Indexes on search fields (name, sku, code)
- Indexes on timestamp fields (audit trail queries)

[OK] **Data Integrity**:
- Proper foreign key constraints
- Cascading deletes where appropriate
- NOT NULL constraints on required fields

[OK] **Multi-Tenancy**:
- Tenant isolation via `tenant_id`
- Row-level security ready (RLS indexes included)

[OK] **Audit Trail**:
- `created_at` timestamps
- `updated_at` timestamps
- Audit logging table

## Prerequisites

- PostgreSQL 12+ with UUID extension
- Empty database recommended (migration drops all existing tables)
- Tenant configuration must be set up separately

## Application

### First Run
```bash
# Backup (important!)
docker exec db pg_dump -U postgres gestiqclouddb_dev > backup_before_migration.sql

# Apply migration
docker exec -i db psql -U postgres -d gestiqclouddb_dev < up.sql

# Verify
docker exec db psql -U postgres -d gestiqclouddb_dev -c "\dt"
```

### Rollback (⚠️ DANGEROUS)
```bash
# This will delete ALL data!
docker exec -i db psql -U postgres -d gestiqclouddb_dev < down.sql
```

## Index Structure

All indexes follow naming convention: `idx_<table>_<column>`

Common index patterns:
- `idx_*_tenant_id` - Multi-tenant queries
- `idx_*_<fk_column>` - Join optimization
- `idx_<table>_<search_column>` - Full-text search fields

## Notes

- This migration is **production-ready**
- Indexes are optimized for the most common queries
- Foreign key constraints use appropriate cascade strategies
- RLS (Row Level Security) can be added in a separate migration
- All column names follow English naming conventions

---

**Status**: ✅ Ready
**Tables**: 74
**Indexes**: 40+
**Generated**: 2025-11-24T11:44:39.089572
