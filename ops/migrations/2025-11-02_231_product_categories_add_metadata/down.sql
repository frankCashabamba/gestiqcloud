BEGIN;

-- Drop index then column (safe order)
DROP INDEX IF EXISTS idx_product_categories_name;
ALTER TABLE IF EXISTS product_categories
  DROP COLUMN IF EXISTS category_metadata;

COMMIT;
