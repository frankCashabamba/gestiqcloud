-- Rollback: remove rows from business_categories
-- Note: only removes the specific rows inserted by up.sql

DELETE FROM public.business_categories
WHERE code IN ('retail', 'services', 'manufacturing', 'food_beverage', 'healthcare', 'education');
