BEGIN;

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a001'::uuid,
    '_system',
    'importador.file_support',
    'accepted_extensions',
    TRUE,
    FALSE,
    1,
    'Accepted extensions',
    '[".pdf",".png",".jpg",".jpeg",".heic",".heif",".tiff",".bmp",".gif",".xlsx",".xls",".csv",".xml",".txt",".zip"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.file_support' AND field = 'accepted_extensions'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a002'::uuid,
    '_system',
    'importador.file_support',
    'image_extensions',
    TRUE,
    FALSE,
    2,
    'Image extensions',
    '[".png",".jpg",".jpeg",".heic",".heif",".tiff",".bmp",".gif"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.file_support' AND field = 'image_extensions'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a003'::uuid,
    '_system',
    'importador.file_support',
    'type_map',
    TRUE,
    FALSE,
    3,
    'File type map',
    '[".pdf=PDF",".jpg=JPG",".jpeg=JPG",".png=PNG",".heic=IMG",".heif=IMG",".tiff=IMG",".bmp=IMG",".gif=IMG",".xlsx=XLSX",".xls=XLS",".csv=CSV",".xml=XML",".txt=TXT",".zip=ZIP"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.file_support' AND field = 'type_map'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a101'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'INVOICE',
    TRUE,
    FALSE,
    1,
    'Invoice patterns',
    '["invoice","factura","rechnung","fattura","fatura","facture"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'INVOICE'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a102'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'RECEIPT',
    TRUE,
    FALSE,
    2,
    'Receipt patterns',
    '["receipt","recibo","boleta","ticket","voucher"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'RECEIPT'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a103'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'BANK_STATEMENT',
    TRUE,
    FALSE,
    3,
    'Bank statement patterns',
    '["bank statement","extracto","estado de cuenta","kontoauszug"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'BANK_STATEMENT'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a104'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'PAYROLL',
    TRUE,
    FALSE,
    4,
    'Payroll patterns',
    '["payroll","nomina","planilla","lohnabrechnung"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'PAYROLL'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a105'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'INVENTORY',
    TRUE,
    FALSE,
    5,
    'Inventory patterns',
    '["inventory","inventario","stock","price list","lista precios"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'INVENTORY'
);

INSERT INTO sector_field_defaults (
    id, sector, module, field, visible, required, ord, label, options
)
SELECT
    '7c0f2d5a-2fe2-4f0f-9f7f-bebfbcb9a106'::uuid,
    '_system',
    'importador.doc_type_patterns',
    'COSTING',
    TRUE,
    FALSE,
    6,
    'Costing patterns',
    '["costing","costeo","recipe","receta","food cost"]'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM sector_field_defaults
    WHERE sector = '_system' AND module = 'importador.doc_type_patterns' AND field = 'COSTING'
);

COMMIT;
