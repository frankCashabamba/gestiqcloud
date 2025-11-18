-- ============================================================================
-- Migration: 2025-11-19_901_fix_table_defaults (DOWN)
-- Description: Rollback defaults
-- ============================================================================

BEGIN;

-- Restore to no default (will fail if records depend on it)
ALTER TABLE IF EXISTS pos_registers
  ALTER COLUMN id DROP DEFAULT;

COMMIT;
