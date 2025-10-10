-- Add tenant_id to datos_importados and backfill from tenants mapping via empresa_id

ALTER TABLE public.datos_importados ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.datos_importados d
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = d.empresa_id
  AND (d.tenant_id IS NULL);

ALTER TABLE public.datos_importados
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_datos_importados_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_datos_importados_tenant_id ON public.datos_importados (tenant_id);

