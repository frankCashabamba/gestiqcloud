-- Migration: Add Fase A classification persistence fields
-- Date: 2025-01-11
-- Purpose: Persist AI classification results in ImportBatch

ALTER TABLE import_batches
ADD COLUMN IF NOT EXISTS suggested_parser VARCHAR(255),
ADD COLUMN IF NOT EXISTS classification_confidence NUMERIC(5,4),
ADD COLUMN IF NOT EXISTS ai_enhanced BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(50);

-- Indices for fast lookups
CREATE INDEX IF NOT EXISTS idx_import_batches_ai_provider ON import_batches(ai_provider);
CREATE INDEX IF NOT EXISTS idx_import_batches_ai_enhanced ON import_batches(ai_enhanced);
