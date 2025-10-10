-- Add tenant_id to payments and backfill from tenants mapping via empresa_id

ALTER TABLE public.payments ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.payments p
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = p.empresa_id
  AND (p.tenant_id IS NULL);

ALTER TABLE public.payments
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_payments_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_payments_tenant_id ON public.payments (tenant_id);

