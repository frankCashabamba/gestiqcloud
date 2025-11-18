-- ============================================================================
-- Migration: 2025-11-19_901_fix_table_defaults
-- Description: Ensure correct defaults for PostgreSQL native functions
-- ============================================================================

BEGIN;

-- Ensure pos_registers.id has gen_random_uuid() default
ALTER TABLE IF EXISTS pos_registers
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

COMMIT;
