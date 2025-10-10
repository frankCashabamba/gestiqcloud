-- Add tenant_id to core_rolempresa and backfill from tenants mapping via empresa_id

ALTER TABLE public.core_rolempresa ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.core_rolempresa c
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = c.empresa_id
  AND (c.tenant_id IS NULL);

ALTER TABLE public.core_rolempresa
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_core_rolempresa_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_core_rolempresa_tenant_id ON public.core_rolempresa (tenant_id);

