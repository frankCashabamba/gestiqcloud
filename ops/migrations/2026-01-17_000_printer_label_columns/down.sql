BEGIN;

ALTER TABLE printer_label_configurations
    DROP COLUMN IF EXISTS columns,
    DROP COLUMN IF EXISTS column_gap_mm;

COMMIT;
