-- Add tenant_id to modulos_empresamodulo and backfill from tenants mapping via empresa_id

ALTER TABLE public.modulos_empresamodulo ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.modulos_empresamodulo m
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = m.empresa_id
  AND (m.tenant_id IS NULL);

ALTER TABLE public.modulos_empresamodulo
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_modulos_empresamodulo_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_modulos_empresamodulo_tenant_id ON public.modulos_empresamodulo (tenant_id);

