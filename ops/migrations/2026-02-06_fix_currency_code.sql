-- Fix currency code from 'US' to 'USD' (ISO 4217 compliant)
-- This migration corrects the currency code that violates the CHECK constraint

BEGIN;

-- Update any currency records with code 'US' to 'USD'
UPDATE currencies 
SET code = 'USD' 
WHERE code = 'US';

-- Update any tenant records with base_currency 'US' to 'USD'
UPDATE tenants 
SET base_currency = 'USD' 
WHERE base_currency = 'US';

COMMIT;
