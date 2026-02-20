-- Ensure products.tax_rate is always populated.
-- This prevents test and runtime inserts from failing on NOT NULL constraints.

ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate SET DEFAULT 0;

UPDATE products
SET tax_rate = 0
WHERE tax_rate IS NULL;

ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate SET NOT NULL;
