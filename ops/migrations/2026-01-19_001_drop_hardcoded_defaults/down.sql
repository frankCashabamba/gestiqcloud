-- Migration: 2026-01-19_001_drop_hardcoded_defaults
-- Description: Restore defaults removed in 2026-01-19_001_drop_hardcoded_defaults.

BEGIN;

ALTER TABLE public.crm_activities ALTER COLUMN type SET DEFAULT 'note'::activitytype;
ALTER TABLE public.crm_activities ALTER COLUMN status SET DEFAULT 'pending'::activitystatus;
ALTER TABLE public.crm_leads ALTER COLUMN status SET DEFAULT 'new'::leadstatus;
ALTER TABLE public.crm_leads ALTER COLUMN source SET DEFAULT 'other'::leadsource;
ALTER TABLE public.crm_opportunities ALTER COLUMN stage SET DEFAULT 'qualification'::opportunitystage;
ALTER TABLE public.crm_opportunities ALTER COLUMN currency SET DEFAULT 'EUR'::character varying;
ALTER TABLE public.doc_number_counters ALTER COLUMN series SET DEFAULT 'A'::character varying;
ALTER TABLE public.import_batches ALTER COLUMN status SET DEFAULT 'PENDING'::character varying;
ALTER TABLE public.import_items ALTER COLUMN status SET DEFAULT 'PENDING'::character varying;
ALTER TABLE public.import_ocr_jobs ALTER COLUMN status SET DEFAULT 'pending'::character varying;
ALTER TABLE public.journal_entries ALTER COLUMN status SET DEFAULT 'DRAFT'::entry_status;
ALTER TABLE public.journal_entries ALTER COLUMN type SET DEFAULT 'OPERATIONS'::character varying;
ALTER TABLE public.sales_orders ALTER COLUMN currency SET DEFAULT 'EUR'::character varying;
ALTER TABLE public.sales_orders ALTER COLUMN status SET DEFAULT 'draft'::character varying;

COMMIT;
