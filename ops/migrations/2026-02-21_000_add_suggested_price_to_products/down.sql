-- Roll back suggested_price and use_suggested_price columns

ALTER TABLE IF EXISTS products
    DROP COLUMN IF EXISTS suggested_price,
    DROP COLUMN IF EXISTS use_suggested_price;
