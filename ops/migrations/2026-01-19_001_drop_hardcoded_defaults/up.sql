-- Migration: 2026-01-19_001_drop_hardcoded_defaults
-- Description: Remove hardcoded defaults so values must be provided explicitly.

BEGIN;

ALTER TABLE public.crm_activities ALTER COLUMN type DROP DEFAULT;
ALTER TABLE public.crm_activities ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.crm_leads ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.crm_leads ALTER COLUMN source DROP DEFAULT;
ALTER TABLE public.crm_opportunities ALTER COLUMN stage DROP DEFAULT;
ALTER TABLE public.crm_opportunities ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE public.doc_number_counters ALTER COLUMN series DROP DEFAULT;
ALTER TABLE public.import_batches ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.import_items ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.import_ocr_jobs ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.journal_entries ALTER COLUMN status DROP DEFAULT;
ALTER TABLE public.journal_entries ALTER COLUMN type DROP DEFAULT;
ALTER TABLE public.sales_orders ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE public.sales_orders ALTER COLUMN status DROP DEFAULT;

COMMIT;
