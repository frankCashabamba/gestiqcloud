-- Add SKU to products and enforce tenant-scoped uniqueness

ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS sku varchar;

-- Backfill SKU for existing rows (id-based placeholder)
UPDATE public.products
SET sku = CONCAT('SKU-', id)
WHERE (sku IS NULL OR sku = '');

-- Enforce NOT NULL
ALTER TABLE public.products
  ALTER COLUMN sku SET NOT NULL;

-- Ensure tenant_id exists (added previously) and create unique constraint
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'public'
      AND table_name = 'products'
      AND constraint_name = 'uq_products_tenant_sku'
  ) THEN
    ALTER TABLE public.products
      ADD CONSTRAINT uq_products_tenant_sku UNIQUE (tenant_id, sku);
  END IF;
END $$;

-- Optional: index for name-based searches
CREATE INDEX IF NOT EXISTS ix_products_name ON public.products (name);

