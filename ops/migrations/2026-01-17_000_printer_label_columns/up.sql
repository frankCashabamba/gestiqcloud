-- Migration: 2026-01-17_000_printer_label_columns
-- Description: Add column layout fields for label printing.

BEGIN;

ALTER TABLE printer_label_configurations
    ADD COLUMN IF NOT EXISTS columns INTEGER,
    ADD COLUMN IF NOT EXISTS column_gap_mm DOUBLE PRECISION;

COMMIT;
