-- =====================================================
-- Migration: 2025-11-19_901_pos_items_table (ROLLBACK)
-- =====================================================

BEGIN;

DROP TABLE IF EXISTS pos_items CASCADE;

COMMIT;
