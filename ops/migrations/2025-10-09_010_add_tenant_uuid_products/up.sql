-- Add tenant_id to products and backfill from tenants mapping via empresa_id

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tenant_id uuid;

DO $$
BEGIN
  -- Backfill only if legacy empresa_id exists
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='products' AND column_name='empresa_id'
  ) THEN
    EXECUTE 'UPDATE public.products p SET tenant_id = t.id FROM public.tenants t WHERE t.empresa_id = p.empresa_id AND p.tenant_id IS NULL';
  END IF;

  -- Create FK if missing (NULLs allowed). Idempotent.
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_products_tenant'
  ) THEN
    EXECUTE 'ALTER TABLE public.products ADD CONSTRAINT fk_products_tenant FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE';
  END IF;

  -- Ensure index exists
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='products' AND indexname='ix_products_tenant_id'
  ) THEN
    EXECUTE 'CREATE INDEX ix_products_tenant_id ON public.products (tenant_id)';
  END IF;

  -- Set NOT NULL only if there are no NULLs remaining
  IF NOT EXISTS (
    SELECT 1 FROM public.products WHERE tenant_id IS NULL
  ) THEN
    EXECUTE 'ALTER TABLE public.products ALTER COLUMN tenant_id SET NOT NULL';
  END IF;
END $$;

-- Nota: mantener empresa_id durante releases de transición; se elimina luego por 2025-10-20_104
