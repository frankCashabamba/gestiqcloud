-- Migration: 2025-12-18_000_assign_next_number
-- Description: Drop assign_next_number function and doc_number_counters table.

BEGIN;

DROP FUNCTION IF EXISTS public.assign_next_number(UUID, TEXT, INTEGER, TEXT);
DROP FUNCTION IF EXISTS public.current_tenant();
DROP TABLE IF EXISTS doc_number_counters;

COMMIT;
