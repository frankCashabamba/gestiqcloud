-- Migration: normalize product field names to English
-- Removes Spanish field name aliases from sector_field_defaults and sector_templates.
-- After applying this migration, remove _FIELD_NAME_CANONICAL from field_config.py
-- Date: 2026-03-18

-- ============================================================
-- 1. sector_field_defaults — rename Spanish field names → English
--    Scope: module = 'productos' (canonical DB key for products)
-- ============================================================

UPDATE public.sector_field_defaults SET field = 'price'
WHERE module = 'productos' AND field IN ('precio', 'precio_venta');

UPDATE public.sector_field_defaults SET field = 'name'
WHERE module = 'productos' AND field = 'nombre';

UPDATE public.sector_field_defaults SET field = 'sku'
WHERE module = 'productos' AND field = 'codigo';

UPDATE public.sector_field_defaults SET field = 'description'
WHERE module = 'productos' AND field = 'descripcion';

UPDATE public.sector_field_defaults SET field = 'tax_rate'
WHERE module = 'productos' AND field IN ('impuesto', 'iva_tasa');

UPDATE public.sector_field_defaults SET field = 'category'
WHERE module = 'productos' AND field = 'categoria';

UPDATE public.sector_field_defaults SET field = 'active'
WHERE module = 'productos' AND field = 'activo';

UPDATE public.sector_field_defaults SET field = 'stock'
WHERE module = 'productos' AND field = 'stock_inicial';

UPDATE public.sector_field_defaults SET field = 'cost_price'
WHERE module = 'productos' AND field = 'precio_compra';

-- ============================================================
-- 2. sector_templates — fix Spanish placeholder keys
--    in template_config -> fields -> products -> placeholders
--
--    Existing Spanish keys per sector:
--      panaderia: codigo, nombre, precio  (sku already present → drop codigo)
--      taller:    codigo, nombre, precio  (sku already present → drop codigo)
--      retail:    codigo, nombre, precio  (sku already present → drop codigo)
--
--    Strategy:
--      a) Remove 'codigo' (duplicate of sku)
--      b) Rename 'nombre' → 'name'
--      c) Rename 'precio' → 'price'
-- ============================================================

-- Helper: only touch rows that actually have the placeholders key
DO $$
DECLARE
  r RECORD;
  cfg jsonb;
  ph  jsonb;
BEGIN
  FOR r IN
    SELECT id, code, template_config
    FROM public.sector_templates
    WHERE template_config #> '{fields,products,placeholders}' IS NOT NULL
  LOOP
    cfg := r.template_config;
    ph  := cfg #> '{fields,products,placeholders}';

    -- a) Remove 'codigo' (legacy Spanish alias of 'sku')
    IF ph ? 'codigo' THEN
      cfg := cfg #- '{fields,products,placeholders,codigo}';
      ph  := cfg #> '{fields,products,placeholders}';
    END IF;

    -- b) Rename 'nombre' → 'name'
    IF ph ? 'nombre' THEN
      cfg := jsonb_set(
        cfg #- '{fields,products,placeholders,nombre}',
        '{fields,products,placeholders,name}',
        ph -> 'nombre'
      );
      ph := cfg #> '{fields,products,placeholders}';
    END IF;

    -- c) Rename 'precio' → 'price'
    IF ph ? 'precio' THEN
      cfg := jsonb_set(
        cfg #- '{fields,products,placeholders,precio}',
        '{fields,products,placeholders,price}',
        ph -> 'precio'
      );
    END IF;

    UPDATE public.sector_templates
    SET template_config = cfg
    WHERE id = r.id;
  END LOOP;
END $$;

-- ============================================================
-- Verify
-- ============================================================
SELECT
  code,
  template_config #> '{fields,products,placeholders}' AS product_placeholders
FROM public.sector_templates
WHERE code IN ('panaderia', 'taller', 'retail')
ORDER BY code;

SELECT module, field, visible, required, ord
FROM public.sector_field_defaults
WHERE module = 'productos'
ORDER BY ord;
