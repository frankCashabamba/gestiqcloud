-- Migration: 2026-01-27_000_fix_test_defaults
-- Purpose: Restore critical defaults and seed minimal values required by tests

BEGIN;

-- Ensure auth_user booleans have server defaults and fix existing nulls
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_active SET DEFAULT true;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_superadmin SET DEFAULT false;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_staff SET DEFAULT false;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN is_verified SET DEFAULT false;
ALTER TABLE IF EXISTS public.auth_user ALTER COLUMN failed_login_count SET DEFAULT 0;
UPDATE public.auth_user
SET is_active = COALESCE(is_active, true),
    is_superadmin = COALESCE(is_superadmin, false),
    is_staff = COALESCE(is_staff, false),
    is_verified = COALESCE(is_verified, false),
    failed_login_count = COALESCE(failed_login_count, 0);

-- company_user_roles needs assigned_at to be not null
ALTER TABLE IF EXISTS public.company_user_roles ALTER COLUMN assigned_at SET DEFAULT now();
UPDATE public.company_user_roles
SET assigned_at = COALESCE(assigned_at, now());

-- sales_orders monetary defaults and status/currency
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN id SET DEFAULT gen_random_uuid();
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN order_date SET DEFAULT now();
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN subtotal SET DEFAULT 0;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN tax SET DEFAULT 0;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN total SET DEFAULT 0;
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN currency SET DEFAULT 'USD';
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN status SET DEFAULT 'draft';
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE IF EXISTS public.sales_orders ALTER COLUMN updated_at SET DEFAULT now();
UPDATE public.sales_orders
SET subtotal = COALESCE(subtotal, 0),
    tax = COALESCE(tax, 0),
    total = COALESCE(total, 0),
    currency = COALESCE(currency, 'USD'),
    status = COALESCE(status, 'draft'),
    order_date = COALESCE(order_date, now()),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now());

-- Tenant currency fallback to avoid currency_not_configured
DO $$
BEGIN
    -- Prefer new base_currency column if present
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tenants'
          AND column_name = 'base_currency'
    ) THEN
        EXECUTE 'ALTER TABLE public.tenants ALTER COLUMN base_currency SET DEFAULT ''USD''';
        EXECUTE 'UPDATE public.tenants SET base_currency = COALESCE(base_currency, ''USD'')';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tenants'
          AND column_name = 'currency'
    ) THEN
        EXECUTE 'ALTER TABLE public.tenants ALTER COLUMN currency SET DEFAULT ''USD''';
        EXECUTE 'UPDATE public.tenants SET currency = COALESCE(currency, ''USD'')';
    END IF;
END $$;

COMMIT;
