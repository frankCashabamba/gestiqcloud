# Migration: 2025-11-20_000_consolidated_final_schema

## Description

Final consolidated schema migration that fixes all inconsistencies between SQLAlchemy models and database schema.

### Changes

#### Column Renames
- `active` → `is_active` in:
  - `business_types`
  - `business_categories`
  - `company_categories`
  - `sector_templates`

#### Columns Added

**business_types:**
- `tenant_id` (UUID FK to tenants)
- `code` (VARCHAR 50, NOT NULL)
- `created_at` (TIMESTAMPTZ, DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

**business_categories:**
- `tenant_id` (UUID FK to tenants)
- `code` (VARCHAR 50)
- `created_at` (TIMESTAMPTZ, DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

**company_categories:**
- `tenant_id` (UUID FK to tenants)
- `code` (VARCHAR 50)
- `description` (TEXT)
- `created_at` (TIMESTAMPTZ, DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

**import_batches:**
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

**sales:**
- `cliente_id` (UUID FK to clients, ON DELETE SET NULL)

**stock_moves:**
- `tentative` (BOOLEAN, NOT NULL, DEFAULT FALSE)

**user_profiles:**
- `tenant_id` (UUID FK to tenants)
- `created_at` (TIMESTAMPTZ, DEFAULT NOW())
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

**sector_templates:**
- `tenant_id` (UUID FK to tenants)
- `code` (VARCHAR 50)
- `updated_at` (TIMESTAMPTZ, DEFAULT NOW())

#### Data Migrations
- Auto-generate `code` values for rows where code is NULL using pattern: `TYPE-<uuid>`, `CAT-<uuid>`, etc.

## Tables Modified
- `business_types`
- `business_categories`
- `company_categories`
- `import_batches`
- `sales`
- `stock_moves`
- `user_profiles`
- `sector_templates`

## Testing
```sql
-- Verify all columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'business_types'
ORDER BY ordinal_position;

-- Verify data integrity
SELECT COUNT(*) FROM business_types WHERE code IS NULL;
```

## Backward Compatibility
- Uses `ALTER COLUMN ... RENAME` to rename `active` to `is_active`
- All columns default to NULL or appropriate defaults
- No data loss
