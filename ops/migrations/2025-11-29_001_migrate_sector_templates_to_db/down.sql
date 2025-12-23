-- Rollback: Eliminar los sector templates migrados
DELETE FROM public.sector_templates
WHERE code IN ('panaderia', 'taller', 'retail');
