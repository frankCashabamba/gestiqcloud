-- Add suggested_price and use_suggested_price columns to products table
-- These columns support the suggested pricing feature based on recipe costs

ALTER TABLE IF EXISTS products
    ADD COLUMN IF NOT EXISTS suggested_price NUMERIC(12, 2) NULL,
    ADD COLUMN IF NOT EXISTS use_suggested_price BOOLEAN DEFAULT FALSE;

-- Ensure use_suggested_price has a default value for existing records
UPDATE products
SET use_suggested_price = FALSE
WHERE use_suggested_price IS NULL;

-- Add a comment to document the feature
COMMENT ON COLUMN products.suggested_price IS 'Auto-calculated price suggestion based on recipe cost (unit_cost * 2 = markup 100%)';
COMMENT ON COLUMN products.use_suggested_price IS 'Flag to apply suggested_price as the selling price';
