-- Migration: 2026-01-21_000_restore_company_users_defaults
-- Description: Restore defaults for company_users verification and login counters.

BEGIN;

ALTER TABLE public.company_users ALTER COLUMN is_verified SET DEFAULT false;
ALTER TABLE public.company_users ALTER COLUMN failed_login_count SET DEFAULT 0;

COMMIT;
