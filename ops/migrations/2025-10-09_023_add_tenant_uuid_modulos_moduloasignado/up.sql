-- Add tenant_id to modulos_moduloasignado and backfill from tenants mapping via empresa_id

ALTER TABLE public.modulos_moduloasignado ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.modulos_moduloasignado m
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = m.empresa_id
  AND (m.tenant_id IS NULL);

ALTER TABLE public.modulos_moduloasignado
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_modulos_moduloasignado_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_modulos_moduloasignado_tenant_id ON public.modulos_moduloasignado (tenant_id);

