-- 103_einv_field_map.sql
-- Mapeo de campos extra (por vertical/plantilla) hacia los payloads SRI/SII.
-- Permite controlar qué `extra` de invoice/product/customer se incluye y cómo, por sector.

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS einv_field_map (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_key text NOT NULL,                   -- 'bazar', 'bakery', ...
  entity text NOT NULL CHECK (entity IN ('invoice','invoice_line','customer','product')),
  country einv_country NOT NULL,                -- 'ES' | 'EC'
  target einv_source NOT NULL,                  -- 'SRI' | 'SII'
  extra_field text NOT NULL,                    -- clave en extra (p.ej. 'warranty_months')
  target_path text NOT NULL,                    -- SRI: XPath (o key de DetalleAdicional); SII: ruta lógica del campo
  required boolean NOT NULL DEFAULT false,
  transformer text,                             -- nombre de función/etiqueta de transformación en backend
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (template_key, entity, country, target, extra_field)
);

-- Ejemplos (opcionales)
-- Bazar: llevar garantía de línea a DetalleAdicional SRI
INSERT INTO einv_field_map(template_key, entity, country, target, extra_field, target_path, required, transformer)
VALUES ('bazar','invoice_line','EC','SRI','warranty_months','DetalleAdicional["Garantía (meses)"]', false, 'to_string')
ON CONFLICT DO NOTHING;

-- Bakery: (ejemplo no fiscal) normalmente NO se envía expiry_date; se deja desactivado por defecto
INSERT INTO einv_field_map(template_key, entity, country, target, extra_field, target_path, required, active)
VALUES ('bakery','product','EC','SRI','expiry_date','DetalleAdicional["Caduca"]', false, false)
ON CONFLICT DO NOTHING;

COMMIT;
