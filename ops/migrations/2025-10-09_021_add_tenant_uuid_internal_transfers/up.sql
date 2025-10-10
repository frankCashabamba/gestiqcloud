-- Add tenant_id to internal_transfers and backfill from tenants mapping via empresa_id

ALTER TABLE public.internal_transfers ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.internal_transfers i
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = i.empresa_id
  AND (i.tenant_id IS NULL);

ALTER TABLE public.internal_transfers
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_internal_transfers_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_internal_transfers_tenant_id ON public.internal_transfers (tenant_id);

