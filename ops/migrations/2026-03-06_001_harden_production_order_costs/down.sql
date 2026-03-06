-- Revert: remove RLS hardening from production_order_costs without dropping data

BEGIN;

DROP POLICY IF EXISTS production_order_costs_tenant_policy ON public.production_order_costs;
ALTER TABLE IF EXISTS public.production_order_costs DISABLE ROW LEVEL SECURITY;

COMMIT;
