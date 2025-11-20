-- Migration: 2025-11-20_906_fix_schema_issues
-- Description: Fix schema issues - missing columns, constraints, and types

BEGIN;

-- Apply missing unique index for import_items idempotency
CREATE UNIQUE INDEX IF NOT EXISTS idx_import_items_tenant_idempotency
    ON import_items(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Add missing taxes column to sales
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS taxes NUMERIC;

-- Fix languages.code column size from VARCHAR(10) to VARCHAR(50)
ALTER TABLE languages
    ALTER COLUMN code TYPE VARCHAR(50);

-- Ensure sales.estado has proper NOT NULL and defaults
ALTER TABLE sales
    ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'nuevo';

COMMIT;
