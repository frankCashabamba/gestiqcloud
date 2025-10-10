-- Add tenant_id to facturas and backfill from tenants mapping via empresa_id

ALTER TABLE public.facturas ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.facturas f
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = f.empresa_id
  AND (f.tenant_id IS NULL);

ALTER TABLE public.facturas
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_facturas_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_facturas_tenant_id ON public.facturas (tenant_id);

-- Mantener empresa_id temporalmente.

