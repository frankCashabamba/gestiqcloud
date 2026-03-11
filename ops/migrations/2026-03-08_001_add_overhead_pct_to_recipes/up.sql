-- Add depreciation/overhead percentage to recipes
-- Represents the percentage on material cost used to amortize
-- equipment, machinery, and infrastructure (typical value: 5%)
ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS overhead_pct NUMERIC(5, 2) DEFAULT 5;
