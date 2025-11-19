-- Migration: 2025-11-20_000_consolidated_final_schema (ROLLBACK)

BEGIN;

-- Rollback column renames (convert back from is_active to active)
ALTER TABLE IF EXISTS business_types
    ALTER COLUMN IF EXISTS is_active RENAME TO active,
    DROP CONSTRAINT IF EXISTS business_types_tenant_code_unique,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS code,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS business_categories
    ALTER COLUMN IF EXISTS is_active RENAME TO active,
    DROP CONSTRAINT IF EXISTS business_categories_tenant_code_unique,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS code,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS company_categories
    ALTER COLUMN IF EXISTS is_active RENAME TO active,
    DROP CONSTRAINT IF EXISTS company_categories_tenant_code_unique,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS code,
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS import_batches
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS sales
    DROP COLUMN IF EXISTS cliente_id;

ALTER TABLE IF EXISTS stock_moves
    DROP COLUMN IF EXISTS tentative;

ALTER TABLE IF EXISTS user_profiles
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS created_at,
    DROP COLUMN IF EXISTS updated_at;

ALTER TABLE IF EXISTS sector_templates
    ALTER COLUMN IF EXISTS is_active RENAME TO active,
    DROP COLUMN IF EXISTS tenant_id,
    DROP COLUMN IF EXISTS code,
    DROP COLUMN IF EXISTS updated_at;

COMMIT;
