-- =====================================================
-- Migration: 2025-11-19_902_pos_receipts_totals
-- Description: Add totals column to pos_receipts
-- =====================================================

BEGIN;

ALTER TABLE pos_receipts
ADD COLUMN IF NOT EXISTS totals JSONB DEFAULT NULL;

COMMIT;
