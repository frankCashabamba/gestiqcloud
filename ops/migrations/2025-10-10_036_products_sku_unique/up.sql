-- Add sku column and unique constraint per tenant when sku is present

ALTER TABLE public.products ADD COLUMN IF NOT EXISTS sku text;

-- Unique per tenant and sku, allow multiple NULLs
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE indexname = 'ux_products_tenant_sku'
  ) THEN
    CREATE UNIQUE INDEX ux_products_tenant_sku ON public.products (tenant_id, sku) WHERE sku IS NOT NULL;
  END IF;
END $$;

