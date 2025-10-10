-- Add tenant_id to bank_accounts and backfill from tenants mapping via empresa_id

ALTER TABLE public.bank_accounts ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE public.bank_accounts b
SET tenant_id = t.id
FROM public.tenants t
WHERE t.empresa_id = b.empresa_id
  AND (b.tenant_id IS NULL);

ALTER TABLE public.bank_accounts
  ALTER COLUMN tenant_id SET NOT NULL,
  ADD CONSTRAINT fk_bank_accounts_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_bank_accounts_tenant_id ON public.bank_accounts (tenant_id);

