-- Migration: 2026-01-19_000_add_missing_db_tables
-- Description: Drop tables added in 2026-01-19_000_add_missing_db_tables.

BEGIN;

DROP TABLE IF EXISTS public.ui_templates CASCADE;
DROP TABLE IF EXISTS public.test_items CASCADE;
DROP TABLE IF EXISTS public.sri_submissions CASCADE;
DROP TABLE IF EXISTS public.sii_batch_items CASCADE;
DROP TABLE IF EXISTS public.sii_batches CASCADE;
DROP TABLE IF EXISTS public.sector_validation_rules CASCADE;
DROP TABLE IF EXISTS public.sector_field_defaults CASCADE;
DROP TABLE IF EXISTS public.einv_credentials CASCADE;
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.deliveries CASCADE;
DROP TABLE IF EXISTS public._migrations CASCADE;

DROP TYPE IF EXISTS sri_status;
DROP TYPE IF EXISTS sii_batch_status;
DROP TYPE IF EXISTS sii_item_status;

COMMIT;
