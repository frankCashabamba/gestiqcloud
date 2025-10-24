-- Add tenant_id to auditoria_importacion and backfill from tenants mapping via empresa_id

ALTER TABLE public.auditoria_importacion ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.auditoria_importacion a
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = a.empresa_id
  AND (a.tenant_id IS NULL);

ALTER TABLE public.auditoria_importacion
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_auditoria_importacion_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_auditoria_importacion_tenant_id ON public.auditoria_importacion (tenant_id);

