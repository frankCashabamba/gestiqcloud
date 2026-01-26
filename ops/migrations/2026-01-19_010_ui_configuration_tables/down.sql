-- Migration: 2026-01-19_010_ui_configuration_tables
-- Rollback: Drop UI configuration tables

BEGIN;

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS public.ui_form_fields CASCADE;
DROP TABLE IF EXISTS public.ui_forms CASCADE;
DROP TABLE IF EXISTS public.ui_filters CASCADE;
DROP TABLE IF EXISTS public.ui_columns CASCADE;
DROP TABLE IF EXISTS public.ui_tables CASCADE;
DROP TABLE IF EXISTS public.ui_widgets CASCADE;
DROP TABLE IF EXISTS public.ui_dashboards CASCADE;
DROP TABLE IF EXISTS public.ui_sections CASCADE;

COMMIT;
