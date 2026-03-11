-- Migration: seed example rows in business_categories
-- Hardcoding removal: load categories from the database
-- Date: November 29, 2025

-- Category seed removed: use the seed script instead (ops/scripts/seed_reference_catalogs.py)

-- No-op to keep the migration pipeline consistent
DO $$
BEGIN
    PERFORM 1;
END $$;
