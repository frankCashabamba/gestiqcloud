-- Rollback: remove the migrated sector templates
DELETE FROM public.sector_templates
WHERE code IN ('panaderia', 'taller', 'retail');
