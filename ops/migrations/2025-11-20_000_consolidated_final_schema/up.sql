-- =====================================================
-- Migration: 2025-11-20_000_consolidated_final_schema
-- Description: Final consolidated schema - fixes all inconsistencies
-- Ensures all tables match SQLAlchemy models exactly
-- =====================================================

BEGIN;

-- =====================================================
-- ALTER existing tables to add missing columns
-- =====================================================

-- business_types: ensure all columns exist
ALTER TABLE IF EXISTS business_types
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ALTER COLUMN IF EXISTS active RENAME TO is_active,
    DROP CONSTRAINT IF EXISTS business_types_tenant_code_unique;

ALTER TABLE business_types
    ADD CONSTRAINT business_types_tenant_code_unique UNIQUE (tenant_id, code);

-- business_categories: ensure all columns exist
ALTER TABLE IF EXISTS business_categories
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ALTER COLUMN IF EXISTS active RENAME TO is_active,
    DROP CONSTRAINT IF EXISTS business_categories_tenant_code_unique;

ALTER TABLE business_categories
    ADD CONSTRAINT business_categories_tenant_code_unique UNIQUE (tenant_id, code);

-- company_categories: ensure all columns exist
ALTER TABLE IF EXISTS company_categories
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ALTER COLUMN IF EXISTS active RENAME TO is_active,
    DROP CONSTRAINT IF EXISTS company_categories_tenant_code_unique;

ALTER TABLE company_categories
    ADD CONSTRAINT company_categories_tenant_code_unique UNIQUE (tenant_id, code);

-- import_batches: add missing columns
ALTER TABLE IF EXISTS import_batches
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- sales: add cliente_id if missing
ALTER TABLE IF EXISTS sales
    ADD COLUMN IF NOT EXISTS cliente_id UUID REFERENCES clients(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_sales_cliente_id ON sales(cliente_id);

-- stock_moves: ensure tentative column exists with proper constraints
ALTER TABLE IF EXISTS stock_moves
    ADD COLUMN IF NOT EXISTS tentative BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_stock_moves_tentative ON stock_moves(tentative);

-- user_profiles: ensure columns match model
ALTER TABLE IF EXISTS user_profiles
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- sector_templates: ensure columns match migration
ALTER TABLE IF EXISTS sector_templates
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ALTER COLUMN IF EXISTS active RENAME TO is_active;

-- =====================================================
-- Create indexes for all modified tables
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_business_types_tenant ON business_types(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_categories_tenant ON business_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_company_categories_tenant ON company_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sector_templates_tenant ON sector_templates(tenant_id);

-- =====================================================
-- Update existing data for compatibility
-- =====================================================

-- Ensure business_types have a code if missing
UPDATE business_types SET code = 'TYPE-' || id::text WHERE code IS NULL;

-- Ensure business_categories have a code if missing
UPDATE business_categories SET code = 'CAT-' || id::text WHERE code IS NULL;

-- Ensure company_categories have a code if missing
UPDATE company_categories SET code = 'COMP-' || id::text WHERE code IS NULL;

-- Ensure sector_templates have a code if missing
UPDATE sector_templates SET code = 'TEMPLATE-' || id::text WHERE code IS NULL;

COMMIT;
