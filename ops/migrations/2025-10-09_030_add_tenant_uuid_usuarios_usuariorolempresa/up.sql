-- Add tenant_id to usuarios_usuariorolempresa and backfill from tenants mapping via empresa_id

ALTER TABLE public.usuarios_usuariorolempresa ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.usuarios_usuariorolempresa u
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = u.empresa_id
  AND (u.tenant_id IS NULL);

ALTER TABLE public.usuarios_usuariorolempresa
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_usuarios_usuariorolempresa_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_usuarios_usuariorolempresa_tenant_id ON public.usuarios_usuariorolempresa (tenant_id);

