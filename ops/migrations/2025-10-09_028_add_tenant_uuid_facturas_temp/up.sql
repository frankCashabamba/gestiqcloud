-- Add tenant_id to facturas_temp and backfill from tenants mapping via empresa_id

ALTER TABLE public.facturas_temp ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.facturas_temp f
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = f.empresa_id
  AND (f.tenant_id IS NULL);

ALTER TABLE public.facturas_temp
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_facturas_temp_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_facturas_temp_tenant_id ON public.facturas_temp (tenant_id);

