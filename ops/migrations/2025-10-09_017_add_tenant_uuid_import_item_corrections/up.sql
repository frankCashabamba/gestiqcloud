-- Add tenant_id to import_item_corrections and backfill from tenants mapping via empresa_id

ALTER TABLE public.import_item_corrections ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.import_item_corrections i
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = i.empresa_id
  AND (i.tenant_id IS NULL);

ALTER TABLE public.import_item_corrections
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_item_corrections_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_import_item_corrections_tenant_id ON public.import_item_corrections (tenant_id);

