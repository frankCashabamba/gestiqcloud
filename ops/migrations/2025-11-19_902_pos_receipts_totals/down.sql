-- =====================================================
-- Migration: 2025-11-19_902_pos_receipts_totals (ROLLBACK)
-- =====================================================

BEGIN;

ALTER TABLE pos_receipts
DROP COLUMN IF EXISTS totals;

COMMIT;
