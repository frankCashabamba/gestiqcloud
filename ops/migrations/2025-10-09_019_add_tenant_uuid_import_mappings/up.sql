-- Add tenant_id to import_mappings and backfill from tenants mapping via empresa_id

ALTER TABLE public.import_mappings ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.import_mappings i
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = i.empresa_id
  AND (i.tenant_id IS NULL);

ALTER TABLE public.import_mappings
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_mappings_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_import_mappings_tenant_id ON public.import_mappings (tenant_id);

