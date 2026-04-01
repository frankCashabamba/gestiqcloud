-- Canonical field: supplier_ref (referencia/código del proveedor en líneas de factura)
-- No tiene projection_column porque vive dentro de line_items (JSON), no en columna propia.
-- Los aliases cubren las variantes más comunes en facturas de proveedores españoles/latinoamericanos.

BEGIN;

INSERT INTO imp_canonical_field (name, field_type, projection_column, active, sort_order)
VALUES ('supplier_ref', 'text', NULL, TRUE, 0)
ON CONFLICT (name) DO NOTHING;

INSERT INTO imp_field_alias (canonical_field, alias, active, priority, source)
VALUES
    ('supplier_ref', 'ref',          TRUE, 10, 'seed'),
    ('supplier_ref', 'ref.',         TRUE, 10, 'seed'),
    ('supplier_ref', 'referencia',   TRUE, 10, 'seed'),
    ('supplier_ref', 'sku',          TRUE, 10, 'seed'),
    ('supplier_ref', 'cod',          TRUE, 10, 'seed'),
    ('supplier_ref', 'cod.',         TRUE, 10, 'seed'),
    ('supplier_ref', 'codigo',       TRUE, 10, 'seed'),
    ('supplier_ref', 'código',       TRUE, 10, 'seed'),
    ('supplier_ref', 'art',          TRUE, 10, 'seed'),
    ('supplier_ref', 'art.',         TRUE, 10, 'seed'),
    ('supplier_ref', 'articulo',     TRUE, 10, 'seed'),
    ('supplier_ref', 'artículo',     TRUE, 10, 'seed'),
    ('supplier_ref', 'cp',           TRUE, 10, 'seed'),
    ('supplier_ref', 'item',         TRUE,  5, 'seed'),
    ('supplier_ref', 'item code',    TRUE, 10, 'seed'),
    ('supplier_ref', 'item_code',    TRUE, 10, 'seed'),
    ('supplier_ref', 'product code', TRUE, 10, 'seed'),
    ('supplier_ref', 'part no',      TRUE, 10, 'seed'),
    ('supplier_ref', 'part_no',      TRUE, 10, 'seed'),
    ('supplier_ref', 'barcode',      TRUE,  5, 'seed'),
    ('supplier_ref', 'ean',          TRUE,  5, 'seed')
ON CONFLICT DO NOTHING;

COMMIT;
