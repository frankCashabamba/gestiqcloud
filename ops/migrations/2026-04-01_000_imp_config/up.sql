-- imp_config: tabla de configuración runtime del módulo importador.
--
-- Reemplaza el uso de sector_field_defaults (sector='_system', module='importador.*')
-- que era un abuso semántico: sector_field_defaults es para configuración UI de
-- formularios por sector de negocio, no para config de sistema del importador.
--
-- Diseño:
--   module      = nombre corto del sub-módulo (sin prefijo 'importador.')
--   key         = nombre de la clave dentro del módulo
--   value_text  = valor escalar: número, string, prompt (nullable)
--   value_list  = valor lista: array JSONB de keywords, reglas, extensiones (nullable)
--   label       = descripción legible para humanos
--
-- Regla de lectura en código:
--   - Usar value_text para scalares (float/string)
--   - Usar value_list para arrays de keywords/reglas

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS imp_config (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    module      VARCHAR(100) NOT NULL,
    key         VARCHAR(100) NOT NULL,
    value_text  TEXT,
    value_list  JSONB,
    label       TEXT,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (module, key)
);

-- ── classification ──────────────────────────────────────────────────────────
ALTER TABLE imp_config
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_config_module_key
    ON imp_config (module, key);

INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('classification', 'confidence_threshold', '0.85',
     'Umbral mínimo de confianza. Documentos por debajo requieren revisión humana.')
ON CONFLICT (module, key) DO NOTHING;

-- ── pre_classifier ──────────────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('pre_classifier', 'min_header_confirmations',   '2',    'Confirmaciones mínimas para confiar en mapeo header→tipo'),
    ('pre_classifier', 'filename_min_confidence',    '0.70', 'Confianza mínima de patrón de filename para pre-clasificar'),
    ('pre_classifier', 'header_coverage_min_ratio',  '0.50', 'Ratio mínimo de headers que deben mapear a campos canónicos'),
    ('pre_classifier', 'structured_skip_threshold',  '0.75', 'Confianza mínima para saltarse la IA en documentos estructurados'),
    ('pre_classifier', 'ocr_weird_ratio_max',        '0.15', 'Ratio máximo de caracteres extraños antes de forzar visión')
ON CONFLICT (module, key) DO NOTHING;

-- ── doc_type_patterns ───────────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('doc_type_patterns', 'INVOICE',
     '["invoice","factura","rechnung","fattura","fatura","facture"]',
     'Palabras clave para detectar facturas'),
    ('doc_type_patterns', 'RECEIPT',
     '["receipt","recibo","boleta","ticket","voucher"]',
     'Palabras clave para detectar recibos/tickets'),
    ('doc_type_patterns', 'BANK_STATEMENT',
     '["bank statement","extracto","estado de cuenta","kontoauszug"]',
     'Palabras clave para extractos bancarios'),
    ('doc_type_patterns', 'PAYROLL',
     '["payroll","nomina","planilla","lohnabrechnung"]',
     'Palabras clave para nóminas'),
    ('doc_type_patterns', 'INVENTORY',
     '["inventory","inventario","stock","price list","lista precios"]',
     'Palabras clave para inventarios'),
    ('doc_type_patterns', 'COSTING',
     '["costing","costeo","recipe","receta","food cost"]',
     'Palabras clave para recetas/costeos')
ON CONFLICT (module, key) DO NOTHING;

-- ── doc_categories ──────────────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('doc_categories', 'invoice',
     '["INVOICE","FACTURA","RECHNUNG","FATTURA","FATURA","FACTURE","CREDIT_NOTE","NOTA_CREDITO","PURCHASE_ORDER","ORDEN_COMPRA","QUOTE","PRESUPUESTO","PROFORMA","DELIVERY_NOTE","DEVIS","BON_DE_COMMANDE","LIEFERSCHEIN","FATTURA_ELETTRONICA","NOTA_FISCAL"]',
     'Doc types que se clasifican como facturas/documentos de compra'),
    ('doc_categories', 'receipt',
     '["RECEIPT","TICKET","VOUCHER","RECIBO","BOLETA","TICKETDEVENTA","REÇU","QUITTUNG","SCONTRINO","NOTA_VENTA","NOTA_DE_VENTA"]',
     'Doc types que se clasifican como recibos/tickets de venta'),
    ('doc_categories', 'recipe',
     '["COSTING","COSTEO","RECIPE","RECETA","KALKULATION","CALCUL_COUT","FOOD_COST","COSTO_PRODUCCION","FICHA_TECNICA"]',
     'Doc types que se clasifican como recetas/costeos'),
    ('doc_categories', 'inventory',
     '["INVENTORY","INVENTARIO","INVENTAR","PRICE_LIST","LISTA_PRECIOS","PREISLISTE","CATALOGUE","CATALOGO","STOCK","BESTANDSLISTE","LISTINO"]',
     'Doc types que se clasifican como inventarios/listas de precios'),
    ('doc_categories', 'bank',
     '["BANK_STATEMENT","EXTRACTO_BANCARIO","KONTOAUSZUG","BANK_MOVEMENTS","MOVIMIENTOS_BANCARIOS","ESTADO_CUENTA","RELEVÉ","EXTRAIT_COMPTE","ESTRATTO_CONTO","ACCOUNT_STATEMENT"]',
     'Doc types que se clasifican como extractos bancarios'),
    ('doc_categories', 'payroll',
     '["PAYROLL","NOMINA","PLANILLA","LOHNABRECHNUNG","BULLETIN_PAIE","ROL_PAGOS","SALARY","BUSTA_PAGA","LIQUIDACION"]',
     'Doc types que se clasifican como nóminas')
ON CONFLICT (module, key) DO NOTHING;

-- ── prompt_config ───────────────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_text, label) VALUES
    ('prompt_config', 'extraction_system',
     'You are a universal accounting document analyzer. Always respond with valid JSON using the configured canonical fields.',
     'System prompt base para extracción de documentos'),
    ('prompt_config', 'structured_table_note',
     'NOTE: Content is already pre-processed as a structured table. If you recognize a list or table, set is_table=true and provide clean column names. Do NOT return individual rows.',
     'Nota adicional para documentos estructurados (CSV/XLSX)'),
    ('prompt_config', 'doc_type_instruction',
     'A short uppercase label describing the document type in English. Use standard business labels when they clearly apply. Use OTHER only if truly unclassifiable.',
     'Instrucción para que el LLM formatee el doc_type')
ON CONFLICT (module, key) DO NOTHING;

INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('prompt_config', 'critical_rules',
     '["The document may be in any language. Read it as-is and map to the configured canonical fields.","total_amount must represent the grand total, not a quantity.","vendor is the entity that issues or signs the document.","If is_table=true, return columns and only visible summary values in fields.","Extract payment_method and payment_terms when visible.","Dates must use YYYY-MM-DD. Amounts must use dot decimal notation. Missing fields must be null.","Do not invent data absent from the document."]',
     'Reglas críticas inyectadas al final del prompt de extracción')
ON CONFLICT (module, key) DO NOTHING;

-- ── file_support ────────────────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('file_support', 'accepted_extensions',
     '[".pdf",".png",".jpg",".jpeg",".heic",".heif",".tiff",".bmp",".gif",".xlsx",".xls",".csv",".xml",".txt",".zip"]',
     'Extensiones de archivo aceptadas por el importador'),
    ('file_support', 'image_extensions',
     '[".png",".jpg",".jpeg",".heic",".heif",".tiff",".bmp",".gif"]',
     'Extensiones consideradas imágenes (usan OCR/visión)'),
    ('file_support', 'type_map',
     '[".pdf=PDF",".jpg=JPG",".jpeg=JPG",".png=PNG",".heic=IMG",".heif=IMG",".tiff=IMG",".bmp=IMG",".gif=IMG",".xlsx=XLSX",".xls=XLS",".csv=CSV",".xml=XML",".txt=TXT",".zip=ZIP"]',
     'Mapeo extensión → tipo interno de archivo')
ON CONFLICT (module, key) DO NOTHING;

-- ── product_sheet_detection ─────────────────────────────────────────────────
INSERT INTO imp_config (module, key, value_list, label) VALUES
    ('product_sheet_detection', 'summary_names',
     '["total","subtotal","resumen","sum","totales"]',
     'Nombres de filas de resumen a ignorar'),
    ('product_sheet_detection', 'name_keywords',
     '["producto","nombre","descripcion","description","item","articulo","product","name","denominacion"]',
     'Keywords para detectar columna de nombre de producto'),
    ('product_sheet_detection', 'price_keywords',
     '["precio unitario","unit price","precio venta","sale price","pvp","price","precio","valor"]',
     'Keywords para detectar columna de precio unitario'),
    ('product_sheet_detection', 'price_reject_keywords',
     '["total","importe total","subtotal"]',
     'Keywords que descartan una columna como precio unitario'),
    ('product_sheet_detection', 'cost_keywords',
     '["costo","cost","compra","purchase"]',
     'Keywords para detectar columna de costo'),
    ('product_sheet_detection', 'sku_keywords',
     '["sku","codigo","code","ean","barcode","referencia","ref"]',
     'Keywords para detectar columna de SKU/código'),
    ('product_sheet_detection', 'category_keywords',
     '["categoria","category","familia","grupo","linea"]',
     'Keywords para detectar columna de categoría'),
    ('product_sheet_detection', 'description_keywords',
     '["descripcion","description","detalle","detalle producto"]',
     'Keywords para detectar columna de descripción larga'),
    ('product_sheet_detection', 'explicit_stock_keywords',
     '["stock","existencia","disponible","inventario","saldo","cantidad stock"]',
     'Keywords que indican claramente columna de stock'),
    ('product_sheet_detection', 'ambiguous_stock_keywords',
     '["cantidad","qty","quantity","unidades","units"]',
     'Keywords ambiguos que pueden ser stock o cantidad de pedido'),
    ('product_sheet_detection', 'operational_keywords',
     '["venta","diaria","sobrante","produc","consumo","merma"]',
     'Keywords operativos que sugieren hoja de producción/consumo'),
    ('product_sheet_detection', 'sheet_hint_keywords',
     '["product","producto","productos","catalog","catalogo","inventory","inventario","stock","price list","lista precios"]',
     'Keywords en nombre de hoja que sugieren hoja de productos')
ON CONFLICT (module, key) DO NOTHING;

-- ── learning ────────────────────────────────────────────────────────────────
-- Pesos del algoritmo de aprendizaje de señales de usuario.
-- Ajustar estos valores cambia cómo el sistema prioriza confirmaciones vs ediciones.
INSERT INTO imp_config (module, key, value_text, label) VALUES
    -- Pesos por tipo de evento (cuánto "vale" cada acción del usuario)
    ('learning', 'event_weight_save',    '4.0',  'Peso de una señal de tipo "save" (el usuario guardó el documento)'),
    ('learning', 'event_weight_confirm', '3.0',  'Peso de una señal de tipo "confirm" (el usuario confirmó sin guardar)'),
    ('learning', 'event_weight_edit',    '1.35', 'Peso de una señal de tipo "edit" (el usuario editó campos antes de confirmar)'),
    ('learning', 'event_weight_default', '1.0',  'Peso para cualquier otro tipo de evento'),
    -- Bonificaciones de calidad de señal (suman al peso base del evento)
    ('learning', 'quality_bonus_required_fields_ok', '0.75',
     'Bonus si la señal tiene required_fields_ok=true en el routing_snapshot'),
    ('learning', 'quality_bonus_no_review_needed',   '0.45',
     'Bonus si la señal tiene needs_human_review=false en el routing_snapshot'),
    ('learning', 'quality_bonus_has_destination',    '0.35',
     'Bonus si la señal tiene chosen_destination definido'),
    -- Confianza base asignada a patrones de filename aprendidos automáticamente
    ('learning', 'filename_pattern_base_confidence', '0.65',
     'Confianza base para patrones de nombre de archivo promovidos por el sistema de aprendizaje')
ON CONFLICT (module, key) DO NOTHING;

COMMIT;
