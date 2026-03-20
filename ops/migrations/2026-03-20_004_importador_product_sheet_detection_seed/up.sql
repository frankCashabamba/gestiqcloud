BEGIN;

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a301'::uuid,
    '_system',
    'importador.product_sheet_detection',
    'summary_names',
    TRUE,
    FALSE,
    1,
    'Summary row names',
    '["total","subtotal","resumen","sum","totales"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'summary_names'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a302'::uuid, '_system', 'importador.product_sheet_detection', 'name_keywords', TRUE, FALSE, 2, 'Name column keywords', '["producto","nombre","descripcion","description","item","articulo","product","name","denominacion"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'name_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a303'::uuid, '_system', 'importador.product_sheet_detection', 'price_keywords', TRUE, FALSE, 3, 'Price column keywords', '["precio unitario","unit price","precio venta","sale price","pvp","price","precio","valor"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'price_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a304'::uuid, '_system', 'importador.product_sheet_detection', 'price_reject_keywords', TRUE, FALSE, 4, 'Price reject keywords', '["total","importe total","subtotal"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'price_reject_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a305'::uuid, '_system', 'importador.product_sheet_detection', 'cost_keywords', TRUE, FALSE, 5, 'Cost column keywords', '["costo","cost","compra","purchase"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'cost_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a306'::uuid, '_system', 'importador.product_sheet_detection', 'sku_keywords', TRUE, FALSE, 6, 'SKU column keywords', '["sku","codigo","code","ean","barcode","referencia","ref"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'sku_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a307'::uuid, '_system', 'importador.product_sheet_detection', 'category_keywords', TRUE, FALSE, 7, 'Category column keywords', '["categoria","category","familia","grupo","linea"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'category_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a308'::uuid, '_system', 'importador.product_sheet_detection', 'description_keywords', TRUE, FALSE, 8, 'Description column keywords', '["descripcion","description","detalle","detalle producto"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'description_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a309'::uuid, '_system', 'importador.product_sheet_detection', 'explicit_stock_keywords', TRUE, FALSE, 9, 'Explicit stock keywords', '["stock","existencia","disponible","inventario","saldo","cantidad stock"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'explicit_stock_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a310'::uuid, '_system', 'importador.product_sheet_detection', 'ambiguous_stock_keywords', TRUE, FALSE, 10, 'Ambiguous stock keywords', '["cantidad","qty","quantity","unidades","units"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'ambiguous_stock_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a311'::uuid, '_system', 'importador.product_sheet_detection', 'operational_keywords', TRUE, FALSE, 11, 'Operational keywords', '["venta","diaria","sobrante","produc","consumo","merma"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'operational_keywords'
);

INSERT INTO sector_field_defaults (id, sector, module, field, visible, required, ord, label, options)
SELECT '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a312'::uuid, '_system', 'importador.product_sheet_detection', 'sheet_hint_keywords', TRUE, FALSE, 12, 'Sheet hint keywords', '["product","producto","productos","catalog","catalogo","inventory","inventario","stock","price list","lista precios"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.product_sheet_detection' AND field = 'sheet_hint_keywords'
);

COMMIT;
