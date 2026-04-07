-- Agrega campos canónicos para columnas de líneas de detalle (line_items).
-- Sin estos campos, el extractor fallback de texto mapea las columnas del PDF
-- a campos de documento incorrrectos:
--   "Descripcion" → concept  (en vez de description)
--   "Importe"     → total_amount (en vez de total_price)
--   "Cantidad", "P. Unitario" → claves crudas sin canónico
-- El frontend espera: description, supplier_ref, quantity, unit_price, total_price.
--
-- NOTA sobre prioridades: se usan valores superiores a los de los campos que
-- actualmente capturan esos alias a nivel de documento (concept.descripcion=8,
-- total_amount.importe=6), para que en la detección de cabecera de tabla ganen
-- los campos de línea. El efecto secundario es mínimo: "Descripcion:" como
-- etiqueta de documento pasa a guardarse como `description` en vez de `concept`,
-- lo que es igualmente válido (el UI no usa la clave concept directamente).

BEGIN;

-- ── Campos canónicos ──────────────────────────────────────────────────────────
INSERT INTO imp_canonical_field (name, field_type, projection_column, sort_order)
VALUES
    ('description', 'text',    NULL, 0),
    ('quantity',    'text',    NULL, 0),
    ('unit_price',  'numeric', NULL, 0),
    ('total_price', 'numeric', NULL, 0)
ON CONFLICT (name) DO NOTHING;

-- ── description ───────────────────────────────────────────────────────────────
-- Prioridad 9 supera concept.descripcion=8 y concept.description=7
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('description', 'description',     TRUE, 10, 'seed'),
    ('description', 'descripcion',     TRUE,  9, 'seed'),
    ('description', 'descripción',     TRUE,  9, 'seed'),
    ('description', 'nombre producto', TRUE,  8, 'seed'),
    ('description', 'nombre_producto', TRUE,  8, 'seed'),
    ('description', 'desc',            TRUE,  6, 'seed')
ON CONFLICT DO NOTHING;

-- ── quantity ──────────────────────────────────────────────────────────────────
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('quantity', 'quantity', TRUE, 10, 'seed'),
    ('quantity', 'cantidad', TRUE, 10, 'seed'),
    ('quantity', 'qty',      TRUE, 10, 'seed'),
    ('quantity', 'cant',     TRUE,  8, 'seed'),
    ('quantity', 'cant.',    TRUE,  8, 'seed'),
    ('quantity', 'unidades', TRUE,  6, 'seed')
ON CONFLICT DO NOTHING;

-- ── unit_price ────────────────────────────────────────────────────────────────
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('unit_price', 'unit_price',      TRUE, 10, 'seed'),
    ('unit_price', 'p. unitario',     TRUE, 10, 'seed'),
    ('unit_price', 'p unitario',      TRUE, 10, 'seed'),
    ('unit_price', 'p.unitario',      TRUE, 10, 'seed'),
    ('unit_price', 'precio unitario', TRUE, 10, 'seed'),
    ('unit_price', 'precio_unitario', TRUE, 10, 'seed'),
    ('unit_price', 'p. unit.',        TRUE,  8, 'seed'),
    ('unit_price', 'precio unit',     TRUE,  8, 'seed')
ON CONFLICT DO NOTHING;

-- ── total_price ───────────────────────────────────────────────────────────────
-- Prioridad 10 supera total_amount.importe=6
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('total_price', 'total_price', TRUE, 10, 'seed'),
    ('total_price', 'importe',     TRUE, 10, 'seed'),
    ('total_price', 'line_total',  TRUE,  8, 'seed'),
    ('total_price', 'total linea', TRUE,  8, 'seed'),
    ('total_price', 'importe line',TRUE,  6, 'seed')
ON CONFLICT DO NOTHING;

COMMIT;
