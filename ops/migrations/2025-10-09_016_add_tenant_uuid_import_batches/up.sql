-- Add tenant_id to import_batches and backfill from tenants mapping via empresa_id

ALTER TABLE public.import_batches ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.import_batches b
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = b.empresa_id
  AND (b.tenant_id IS NULL);

ALTER TABLE public.import_batches
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_import_batches_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_import_batches_tenant_id ON public.import_batches (tenant_id);

