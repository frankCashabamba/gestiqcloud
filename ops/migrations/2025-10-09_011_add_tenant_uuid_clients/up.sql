-- Add tenant_id to clients and backfill from tenants mapping via empresa_id

ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.clients c
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = c.empresa_id
  AND (c.tenant_id IS NULL);

ALTER TABLE public.clients
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_clients_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_clients_tenant_id ON public.clients (tenant_id);

-- Mantener empresa_id temporalmente.

