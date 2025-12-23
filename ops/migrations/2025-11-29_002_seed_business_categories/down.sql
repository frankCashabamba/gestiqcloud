-- Rollback: Eliminar datos de business_categories
-- Nota: Solo elimina los datos específicos que se insertaron en up.sql

DELETE FROM public.business_categories
WHERE code IN ('retail', 'services', 'manufacturing', 'food_beverage', 'healthcare', 'education');
