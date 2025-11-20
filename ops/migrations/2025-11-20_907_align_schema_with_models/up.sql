-- Migration: 2025-11-20_907_align_schema_with_models
-- Description: Align database schema with SQLAlchemy models
-- Fixes: sales table columns to match venta.py model (Spanish names)
--        import_items table constraints and indexes
--        business_types tenant_id constraint
--        Ensure all test fixtures work

BEGIN;

-- ============================================================================
-- Fix sales table to match venta.py model
-- ============================================================================

-- 1. Drop existing constraints that conflict
ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_customer_id_fkey CASCADE;

-- 2. Handle column alignment: rename OR drop duplicates
DO $$
BEGIN
    -- If customer_id exists and cliente_id doesn't, rename
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'customer_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'cliente_id') THEN
        ALTER TABLE sales RENAME COLUMN customer_id TO cliente_id;
    -- If both exist, drop the English version
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'customer_id')
       AND EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'cliente_id') THEN
        ALTER TABLE sales DROP COLUMN customer_id;
    END IF;

    -- If sale_date exists and fecha doesn't, rename
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'sale_date')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'fecha') THEN
        ALTER TABLE sales RENAME COLUMN sale_date TO fecha;
    -- If both exist, drop the English version
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'sale_date')
       AND EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'fecha') THEN
        ALTER TABLE sales DROP COLUMN sale_date;
    END IF;

    -- If tax exists and taxes doesn't, rename
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'tax')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'taxes') THEN
        ALTER TABLE sales RENAME COLUMN tax TO taxes;
    -- If both exist, drop the English version
    ELSIF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'tax')
       AND EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'taxes') THEN
        ALTER TABLE sales DROP COLUMN tax;
    END IF;
END $$;

-- 3. Add missing columns if not exist
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS notas TEXT,
    ADD COLUMN IF NOT EXISTS usuario_id UUID DEFAULT gen_random_uuid() NOT NULL,
    ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'draft';

-- 4. Make cliente_id nullable (as per model)
DO $$
BEGIN
    -- Only drop constraint if column is NOT NULL
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sales' AND column_name = 'cliente_id'
               AND is_nullable = 'NO') THEN
        ALTER TABLE sales ALTER COLUMN cliente_id DROP NOT NULL;
    END IF;
END $$;

-- 5. Add foreign key for cliente_id with correct constraint name (ignore if exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE table_name = 'sales' AND constraint_name = 'sales_cliente_id_fkey') THEN
        ALTER TABLE sales
            ADD CONSTRAINT sales_cliente_id_fkey
            FOREIGN KEY (cliente_id) REFERENCES clients(id) ON DELETE SET NULL;
    END IF;
END $$;

-- 6. Drop unused columns that aren't in the model
ALTER TABLE sales DROP COLUMN IF EXISTS sales_order_id;

-- 7. Update indexes
DROP INDEX IF EXISTS idx_sales_customer;
CREATE INDEX IF NOT EXISTS idx_sales_cliente_id ON sales(cliente_id);
DROP INDEX IF EXISTS idx_sales_date;
CREATE INDEX IF NOT EXISTS idx_sales_fecha ON sales(fecha);

-- ============================================================================
-- Fix business_types table - ensure tenant_id is NULLABLE (per model)
-- ============================================================================

-- Ensure tenant_id exists and is nullable (as per BusinessType model)
ALTER TABLE business_types
    ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE;

-- Make sure it's nullable (NOT NOT NULL)
DO $$
BEGIN
    -- Only drop constraint if column is NOT NULL
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'business_types' AND column_name = 'tenant_id'
               AND is_nullable = 'NO') THEN
        ALTER TABLE business_types ALTER COLUMN tenant_id DROP NOT NULL;
    END IF;
END $$;

-- ============================================================================
-- Fix import_items table - proper unique constraint for idempotency
-- ============================================================================

-- Drop old ON CONFLICT index if it exists with wrong definition
DROP INDEX IF EXISTS idx_import_items_tenant_idempotency;

-- Create proper unique constraint for ON CONFLICT DO NOTHING
CREATE UNIQUE INDEX IF NOT EXISTS idx_import_items_tenant_idempotency
    ON import_items(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- ============================================================================
-- Fix stock_moves table - warehouse_id foreign key
-- ============================================================================

-- Ensure warehouse_id FK exists properly
ALTER TABLE stock_moves DROP CONSTRAINT IF EXISTS stock_moves_warehouse_id_fkey;
ALTER TABLE stock_moves
    ADD CONSTRAINT stock_moves_warehouse_id_fkey
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT;

-- ============================================================================
-- Fix company_users table - id column type must be UUID
-- ============================================================================

-- company_users.id should be UUID, not integer
-- Only convert if it's currently an integer type
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'company_users' AND column_name = 'id'
               AND data_type = 'integer') THEN
        ALTER TABLE company_users ALTER COLUMN id TYPE UUID USING gen_random_uuid();
    END IF;
END $$;

COMMIT;
