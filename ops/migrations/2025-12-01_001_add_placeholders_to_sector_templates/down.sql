-- Reversión: Remover placeholders de sector_templates.template_config
-- Si es necesario volver atrás, elimina los placeholders agregados

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,inventory,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,products,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,customers,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,expenses,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,accounting,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,hr,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,suppliers,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,importing,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,roles,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,vacation,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,categories,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,pos,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,alerts,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,accounting_plan,placeholders}',
  'null'::jsonb
)
WHERE code IN ('panaderia', 'taller', 'retail');
