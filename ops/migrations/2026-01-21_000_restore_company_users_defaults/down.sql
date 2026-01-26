-- Migration: 2026-01-21_000_restore_company_users_defaults
-- Description: Drop defaults for company_users verification and login counters.

BEGIN;

ALTER TABLE public.company_users ALTER COLUMN is_verified DROP DEFAULT;
ALTER TABLE public.company_users ALTER COLUMN failed_login_count DROP DEFAULT;

COMMIT;
