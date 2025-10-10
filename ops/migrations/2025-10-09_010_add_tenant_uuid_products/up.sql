-- Add tenant_id to products and backfill from tenants mapping via empresa_id

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.products p
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = p.empresa_id
  AND (p.tenant_id IS NULL);

ALTER TABLE public.products
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_products_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_products_tenant_id ON public.products (tenant_id);

-- Nota: mantener empresa_id durante releases de transición; se elimina luego.

