-- Migration: 2025-11-19_903_add_parser_fields
-- Description: Add parser_id and related fields to import_batches, add canonical_doc to import_items

BEGIN;

-- Add parser fields to import_batches
ALTER TABLE import_batches
    ADD COLUMN IF NOT EXISTS parser_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS parser_choice_confidence NUMERIC,
    ADD COLUMN IF NOT EXISTS suggested_parser VARCHAR(100),
    ADD COLUMN IF NOT EXISTS classification_confidence NUMERIC,
    ADD COLUMN IF NOT EXISTS ai_enhanced BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50);

-- Add updated_at for audit
ALTER TABLE import_batches
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- Add canonical_doc to import_items for parser output
ALTER TABLE import_items
    ADD COLUMN IF NOT EXISTS canonical_doc JSONB;

-- Add unique index for idempotency on import_items
CREATE UNIQUE INDEX IF NOT EXISTS idx_import_items_tenant_idempotency
    ON import_items(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMIT;
