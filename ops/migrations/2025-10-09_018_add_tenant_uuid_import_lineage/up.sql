-- Add tenant_id to import_lineage and backfill from tenants mapping via empresa_id

ALTER TABLE public.import_lineage ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.import_lineage i
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = i.empresa_id
  AND (i.tenant_id IS NULL);

ALTER TABLE public.import_lineage
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_lineage_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_import_lineage_tenant_id ON public.import_lineage (tenant_id);

