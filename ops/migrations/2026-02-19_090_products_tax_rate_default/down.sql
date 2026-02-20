-- Roll back tax_rate defaults/constraints if needed.

ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate DROP NOT NULL;

ALTER TABLE IF EXISTS products
    ALTER COLUMN tax_rate DROP DEFAULT;
