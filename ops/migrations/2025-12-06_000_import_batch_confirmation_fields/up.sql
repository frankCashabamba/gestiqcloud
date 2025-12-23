-- Migration: Add confirmation fields to import_batches table
-- Date: 2025-12-06
-- Description: Adds fields for confirmation flow when classification confidence is low

-- Add requires_confirmation field (default false for existing records)
ALTER TABLE import_batches 
ADD COLUMN IF NOT EXISTS requires_confirmation BOOLEAN DEFAULT FALSE;

-- Add confirmed_at timestamp
ALTER TABLE import_batches 
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP;

-- Add confirmed_parser (parser chosen after confirmation)
ALTER TABLE import_batches 
ADD COLUMN IF NOT EXISTS confirmed_parser VARCHAR(100);

-- Add user_override flag (true if user chose different parser than suggested)
ALTER TABLE import_batches 
ADD COLUMN IF NOT EXISTS user_override BOOLEAN DEFAULT FALSE;

-- Add index for querying batches requiring confirmation
CREATE INDEX IF NOT EXISTS idx_import_batches_requires_confirmation 
ON import_batches(requires_confirmation) 
WHERE requires_confirmation = TRUE;

-- Add comment for documentation
COMMENT ON COLUMN import_batches.requires_confirmation IS 'True if classification confidence was below threshold and user must confirm';
COMMENT ON COLUMN import_batches.confirmed_at IS 'Timestamp when user confirmed the parser selection';
COMMENT ON COLUMN import_batches.confirmed_parser IS 'Parser ID chosen by user during confirmation';
COMMENT ON COLUMN import_batches.user_override IS 'True if user chose a different parser than the suggested one';
