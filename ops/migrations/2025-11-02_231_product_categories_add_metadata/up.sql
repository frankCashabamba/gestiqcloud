BEGIN;

-- Add missing JSONB metadata column expected by ORM
ALTER TABLE IF EXISTS product_categories
  ADD COLUMN IF NOT EXISTS category_metadata JSONB;

-- Helpful for ORDER BY/filters on name
CREATE INDEX IF NOT EXISTS idx_product_categories_name ON product_categories(name);

COMMIT;

