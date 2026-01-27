-- Rollback: revert defaults added in 2026-01-27_000_fix_test_defaults

BEGIN;

ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_active DROP DEFAULT;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_superadmin DROP DEFAULT;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_staff DROP DEFAULT;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_verified DROP DEFAULT;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN failed_login_count DROP DEFAULT;

ALTER TABLE IF EXISTS public.company_user_roles ALTER COLUMN assigned_at DROP DEFAULT;

ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN order_date DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN subtotal DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN tax DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN total DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN currency DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN status DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN created_at DROP DEFAULT;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN updated_at DROP DEFAULT;

ALTER TABLE IF EXISTS public.tenants ALTER COLUMN currency DROP DEFAULT;

COMMIT;
