-- Migration: 2026-03-06_001_harden_production_order_costs
-- Description: Ensure production_order_costs exists and is hardened with defaults, indexes, comments, and RLS.

BEGIN;

DO $$
BEGIN
    IF to_regclass('public.production_orders') IS NULL THEN
        RAISE EXCEPTION 'production_orders table is required before production_order_costs';
    END IF;
    IF to_regclass('public.production_cost_drivers') IS NULL THEN
        RAISE EXCEPTION 'production_cost_drivers table is required before production_order_costs';
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.production_order_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES public.production_orders(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES public.production_cost_drivers(id) ON DELETE RESTRICT,
    qty_actual NUMERIC(12,4) NOT NULL DEFAULT 0,
    headcount_actual INTEGER NOT NULL DEFAULT 1,
    rate_applied NUMERIC(12,4) NOT NULL DEFAULT 0,
    cost_total NUMERIC(12,4) GENERATED ALWAYS AS (qty_actual * rate_applied * headcount_actual) STORED,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS order_id UUID;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS driver_id UUID;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS qty_actual NUMERIC(12,4) NOT NULL DEFAULT 0;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS headcount_actual INTEGER NOT NULL DEFAULT 1;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS rate_applied NUMERIC(12,4) NOT NULL DEFAULT 0;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS notes TEXT;

ALTER TABLE public.production_order_costs
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'production_order_costs'
          AND column_name = 'cost_total'
    ) THEN
        ALTER TABLE public.production_order_costs
            ADD COLUMN cost_total NUMERIC(12,4)
            GENERATED ALWAYS AS (qty_actual * rate_applied * headcount_actual) STORED;
    END IF;
END
$$;

ALTER TABLE public.production_order_costs
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE public.production_order_costs
    ALTER COLUMN qty_actual SET DEFAULT 0;

ALTER TABLE public.production_order_costs
    ALTER COLUMN headcount_actual SET DEFAULT 1;

ALTER TABLE public.production_order_costs
    ALTER COLUMN rate_applied SET DEFAULT 0;

ALTER TABLE public.production_order_costs
    ALTER COLUMN created_at SET DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'production_order_costs_order_id_fkey'
          AND conrelid = 'public.production_order_costs'::regclass
    ) THEN
        ALTER TABLE public.production_order_costs
            ADD CONSTRAINT production_order_costs_order_id_fkey
            FOREIGN KEY (order_id)
            REFERENCES public.production_orders(id)
            ON DELETE CASCADE;
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'production_order_costs_driver_id_fkey'
          AND conrelid = 'public.production_order_costs'::regclass
    ) THEN
        ALTER TABLE public.production_order_costs
            ADD CONSTRAINT production_order_costs_driver_id_fkey
            FOREIGN KEY (driver_id)
            REFERENCES public.production_cost_drivers(id)
            ON DELETE RESTRICT;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_prod_order_costs_order
    ON public.production_order_costs(order_id);

CREATE INDEX IF NOT EXISTS idx_prod_order_costs_driver
    ON public.production_order_costs(driver_id);

COMMENT ON TABLE public.production_order_costs IS 'Actual indirect costs recorded per production batch';
COMMENT ON COLUMN public.production_order_costs.cost_total IS 'Auto-calculated: qty_actual * rate_applied * headcount_actual';

ALTER TABLE public.production_order_costs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'production_order_costs'
          AND policyname = 'production_order_costs_tenant_policy'
    ) THEN
        CREATE POLICY production_order_costs_tenant_policy
        ON public.production_order_costs
        USING (
            EXISTS (
                SELECT 1
                FROM public.production_orders po
                WHERE po.id = order_id
                  AND po.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
        )
        WITH CHECK (
            EXISTS (
                SELECT 1
                FROM public.production_orders po
                WHERE po.id = order_id
                  AND po.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            )
        );
    END IF;
END
$$;

COMMIT;
