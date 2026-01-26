-- Migration: Add `pos_invoice_lines` table for POSLine polymorphic model
-- Date: 2026-01-22
-- Purpose: Support SQLAlchemy polymorphic inheritance with sector='pos'

DO $$
BEGIN
    -- Check if invoice_lines table exists (should exist from consolidated schema)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'invoice_lines') THEN

        -- Create pos_invoice_lines table (joined table inheritance)
        CREATE TABLE IF NOT EXISTS pos_invoice_lines (
            id UUID NOT NULL PRIMARY KEY,
            pos_receipt_line_id UUID,
            FOREIGN KEY (id) REFERENCES invoice_lines(id) ON DELETE CASCADE
        );

        -- Index for pos_receipt_line_id lookups
        CREATE INDEX IF NOT EXISTS idx_pos_invoice_lines_pos_receipt_line_id
            ON pos_invoice_lines(pos_receipt_line_id);

        -- Optional: Composite index for tenant + pos_receipt_id (for better query planning)
        -- Useful for queries like: SELECT * FROM pos_invoice_lines WHERE pos_receipt_line_id = ?

    END IF;
END $$;
