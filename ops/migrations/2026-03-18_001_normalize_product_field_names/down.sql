-- Rollback: restore Spanish field name aliases
-- Date: 2026-03-18

-- ============================================================
-- 1. sector_field_defaults — restore Spanish field names
-- ============================================================

UPDATE public.sector_field_defaults SET field = 'precio'
WHERE module = 'productos' AND field = 'price';

UPDATE public.sector_field_defaults SET field = 'nombre'
WHERE module = 'productos' AND field = 'name';

UPDATE public.sector_field_defaults SET field = 'codigo'
WHERE module = 'productos' AND field = 'sku';

UPDATE public.sector_field_defaults SET field = 'descripcion'
WHERE module = 'productos' AND field = 'description';

UPDATE public.sector_field_defaults SET field = 'iva_tasa'
WHERE module = 'productos' AND field = 'tax_rate';

UPDATE public.sector_field_defaults SET field = 'categoria'
WHERE module = 'productos' AND field = 'category';

UPDATE public.sector_field_defaults SET field = 'activo'
WHERE module = 'productos' AND field = 'active';

UPDATE public.sector_field_defaults SET field = 'stock_inicial'
WHERE module = 'productos' AND field = 'stock';

UPDATE public.sector_field_defaults SET field = 'precio_compra'
WHERE module = 'productos' AND field = 'cost_price';

-- ============================================================
-- 2. sector_templates — restore Spanish placeholder keys
-- ============================================================

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

    -- Restore 'price' → 'precio'
    IF ph ? 'price' THEN
      cfg := jsonb_set(
        cfg #- '{fields,products,placeholders,price}',
        '{fields,products,placeholders,precio}',
        ph -> 'price'
      );
      ph := cfg #> '{fields,products,placeholders}';
    END IF;

    -- Restore 'name' → 'nombre'
    IF ph ? 'name' THEN
      cfg := jsonb_set(
        cfg #- '{fields,products,placeholders,name}',
        '{fields,products,placeholders,nombre}',
        ph -> 'name'
      );
      ph := cfg #> '{fields,products,placeholders}';
    END IF;

    -- Re-add 'codigo' (was removed in up.sql as duplicate of sku)
    IF ph ? 'sku' THEN
      cfg := jsonb_set(
        cfg,
        '{fields,products,placeholders,codigo}',
        ph -> 'sku'
      );
    END IF;

    UPDATE public.sector_templates
    SET template_config = cfg
    WHERE id = r.id;
  END LOOP;
END $$;
