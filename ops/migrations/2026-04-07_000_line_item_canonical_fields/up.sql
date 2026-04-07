-- Añade line_item_slot y label a imp_canonical_field.
-- line_item_slot: nombre del slot estándar que usará el frontend (null = campo de documento).
-- label:         etiqueta legible para mostrar en UI (null = derivar del nombre).
--
-- Con estos dos campos, el auto-aprendizaje puede crear canonical fields nuevos
-- (cuando encuentra columnas desconocidas en tablas) y asignarles un slot estándar
-- por fuzzy-matching. El frontend lee los slots desde la BD y renderiza dinámicamente
-- sin ningún nombre de campo hardcodeado.

BEGIN;

ALTER TABLE imp_canonical_field
    ADD COLUMN IF NOT EXISTS line_item_slot VARCHAR(50),
    ADD COLUMN IF NOT EXISTS label          VARCHAR(100);

-- supplier_ref ya existe, solo añadirle slot y label
UPDATE imp_canonical_field
SET line_item_slot = 'supplier_ref',
    label          = 'Ref. proveedor'
WHERE name = 'supplier_ref';

-- Los 4 slots estándar de líneas de detalle
INSERT INTO imp_canonical_field (name, field_type, projection_column, line_item_slot, label, sort_order)
VALUES
    ('description', 'text',    NULL, 'description', 'Descripción',  0),
    ('quantity',    'text',    NULL, 'quantity',    'Cantidad',      0),
    ('unit_price',  'numeric', NULL, 'unit_price',  'P. Unitario',   0),
    ('total_price', 'numeric', NULL, 'total_price', 'Total',         0)
ON CONFLICT (name) DO UPDATE SET
    line_item_slot = EXCLUDED.line_item_slot,
    label          = EXCLUDED.label;

-- Aliases para description
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

-- Aliases para quantity
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('quantity', 'quantity', TRUE, 10, 'seed'),
    ('quantity', 'cantidad', TRUE, 10, 'seed'),
    ('quantity', 'qty',      TRUE, 10, 'seed'),
    ('quantity', 'cant',     TRUE,  8, 'seed'),
    ('quantity', 'cant.',    TRUE,  8, 'seed'),
    ('quantity', 'unidades', TRUE,  6, 'seed')
ON CONFLICT DO NOTHING;

-- Aliases para unit_price
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

-- Aliases para total_price
-- Prioridad 10 supera total_amount.importe=6
INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('total_price', 'total_price', TRUE, 10, 'seed'),
    ('total_price', 'importe',     TRUE, 10, 'seed'),
    ('total_price', 'line_total',  TRUE,  8, 'seed'),
    ('total_price', 'total linea', TRUE,  8, 'seed')
ON CONFLICT DO NOTHING;

COMMIT;
