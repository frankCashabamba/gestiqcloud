-- Aliases de campos canónicos configurables desde BD
-- Reemplaza las listas hardcodeadas en document_fields.py
CREATE TABLE IF NOT EXISTS imp_field_alias (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id) ON DELETE CASCADE,
    -- NULL = alias global del sistema, válido para todos los tenants
    canonical_field VARCHAR(50)  NOT NULL,
    alias           VARCHAR(100) NOT NULL,
    priority        INTEGER      NOT NULL DEFAULT 0,
    active          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, canonical_field, alias)
);
CREATE INDEX ON imp_field_alias (canonical_field) WHERE active = TRUE;
CREATE INDEX ON imp_field_alias (tenant_id) WHERE tenant_id IS NOT NULL;

-- Tipos de documento configurables desde BD
-- Reemplaza _EMERGENCY_PATTERNS en ai_classifier.py y _BUILTIN_FALLBACK en category_loader.py
CREATE TABLE IF NOT EXISTS imp_doc_type (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID    REFERENCES tenants(id) ON DELETE CASCADE,
    code        VARCHAR(50)  NOT NULL,
    aliases     TEXT[]       NOT NULL DEFAULT '{}',
    category    VARCHAR(30)  NOT NULL,
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order  INTEGER      NOT NULL DEFAULT 0,
    UNIQUE (tenant_id, code)
);
CREATE INDEX ON imp_doc_type (category) WHERE active = TRUE;

-- Códigos de error estructurados con metadatos para el frontend
CREATE TABLE IF NOT EXISTS imp_error_code (
    code            VARCHAR(80)  PRIMARY KEY,
    category        VARCHAR(30)  NOT NULL,
    description     TEXT         NOT NULL,
    resolvable_by   VARCHAR(30)  NOT NULL,
    affected_fields TEXT[]       NOT NULL DEFAULT '{}',
    active          BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Seed inicial de error codes
INSERT INTO imp_error_code (code, category, description, resolvable_by, affected_fields) VALUES
  ('MISSING_AMOUNT',   'validation', 'El monto total no se encontró o es cero',         'field_revision',  ARRAY['total_amount']),
  ('INVALID_DATE',     'validation', 'La fecha no tiene formato válido',                 'field_revision',  ARRAY['issue_date']),
  ('MISSING_VENDOR',   'validation', 'No se detectó proveedor',                          'field_revision',  ARRAY['vendor', 'vendor_tax_id']),
  ('DUPLICATE_RECORD', 'logic',      'Ya existe un registro idéntico en destino',        'skip_or_force',   ARRAY[]::TEXT[]),
  ('UNMATCHED_ACCOUNT','mapping',    'No se encontró cuenta contable para esta línea',   'manual_mapping',  ARRAY[]::TEXT[]),
  ('COLUMN_UNMAPPED',  'mapping',    'Columna del fichero sin campo canónico asignado',  'column_mapping',  ARRAY[]::TEXT[]),
  ('INVALID_CURRENCY', 'validation', 'Código de moneda no reconocido',                   'field_revision',  ARRAY['currency']),
  ('MISSING_REQUIRED', 'validation', 'Falta un campo obligatorio',                       'field_revision',  ARRAY[]::TEXT[]),
  ('SYSTEM_ERROR',     'system',     'Error interno al procesar la línea',               'retry',           ARRAY[]::TEXT[]),
  ('PARSE_ERROR',      'parsing',    'La línea no pudo parsearse del fichero',           'manual_fix',      ARRAY[]::TEXT[])
ON CONFLICT (code) DO NOTHING;

-- Seed inicial de aliases de campos (globales, tenant_id = NULL)
INSERT INTO imp_field_alias (tenant_id, canonical_field, alias, priority) VALUES
  -- total_amount
  (NULL, 'total_amount', 'total_amount',   10),
  (NULL, 'total_amount', 'monto_total',    9),
  (NULL, 'total_amount', 'total',          8),
  (NULL, 'total_amount', 'amount',         7),
  (NULL, 'total_amount', 'importe',        6),
  (NULL, 'total_amount', 'grand_total',    5),
  (NULL, 'total_amount', 'total_general',  4),
  -- subtotal
  (NULL, 'subtotal', 'subtotal',           10),
  (NULL, 'subtotal', 'base_imponible',     9),
  (NULL, 'subtotal', 'neto',               8),
  (NULL, 'subtotal', 'monto',              7),
  (NULL, 'subtotal', 'amount_before_tax',  6),
  -- tax_amount
  (NULL, 'tax_amount', 'tax_amount',       10),
  (NULL, 'tax_amount', 'iva',              9),
  (NULL, 'tax_amount', 'tax',              8),
  (NULL, 'tax_amount', 'vat',              7),
  (NULL, 'tax_amount', 'impuesto',         6),
  (NULL, 'tax_amount', 'igv',              5),
  -- issue_date
  (NULL, 'issue_date', 'issue_date',       10),
  (NULL, 'issue_date', 'fecha',            9),
  (NULL, 'issue_date', 'date',             8),
  (NULL, 'issue_date', 'invoice_date',     7),
  (NULL, 'issue_date', 'expense_date',     6),
  -- currency
  (NULL, 'currency', 'currency',           10),
  (NULL, 'currency', 'moneda',             9),
  (NULL, 'currency', 'divisa',             8),
  -- vendor
  (NULL, 'vendor', 'vendor',               10),
  (NULL, 'vendor', 'vendor_name',          9),
  (NULL, 'vendor', 'supplier',             8),
  (NULL, 'vendor', 'proveedor',            7),
  (NULL, 'vendor', 'emisor',               6),
  (NULL, 'vendor', 'issuer',               5),
  -- vendor_tax_id
  (NULL, 'vendor_tax_id', 'vendor_tax_id',     10),
  (NULL, 'vendor_tax_id', 'supplier_tax_id',   9),
  (NULL, 'vendor_tax_id', 'tax_id',            8),
  (NULL, 'vendor_tax_id', 'ruc',               7),
  (NULL, 'vendor_tax_id', 'ruc_proveedor',     6),
  -- customer
  (NULL, 'customer', 'customer',           10),
  (NULL, 'customer', 'customer_name',      9),
  (NULL, 'customer', 'cliente',            8),
  -- customer_tax_id
  (NULL, 'customer_tax_id', 'customer_tax_id', 10),
  (NULL, 'customer_tax_id', 'client_tax_id',   9),
  (NULL, 'customer_tax_id', 'ruc_cliente',     8),
  -- doc_number
  (NULL, 'doc_number', 'doc_number',           10),
  (NULL, 'doc_number', 'document_number',      9),
  (NULL, 'doc_number', 'invoice_number',       8),
  (NULL, 'doc_number', 'numero_documento',     7),
  (NULL, 'doc_number', 'numero_factura',       6),
  (NULL, 'doc_number', 'numero',               5),
  -- payment_method
  (NULL, 'payment_method', 'payment_method',   10),
  (NULL, 'payment_method', 'payment_type',     9),
  (NULL, 'payment_method', 'payment_mode',     8),
  (NULL, 'payment_method', 'metodo_pago',      7),
  (NULL, 'payment_method', 'metodo_de_pago',   6),
  (NULL, 'payment_method', 'forma_pago',       5),
  (NULL, 'payment_method', 'forma_de_pago',    4),
  (NULL, 'payment_method', 'tipo_pago',        3),
  (NULL, 'payment_method', 'tipo_de_pago',     2),
  (NULL, 'payment_method', 'medio_pago',       2),
  (NULL, 'payment_method', 'medio_de_pago',    1),
  -- payment_terms
  (NULL, 'payment_terms', 'payment_terms',     10),
  (NULL, 'payment_terms', 'terms_of_payment',  9),
  (NULL, 'payment_terms', 'condicion_pago',    8),
  (NULL, 'payment_terms', 'condiciones_pago',  7),
  -- line_items
  (NULL, 'line_items', 'line_items',           10),
  (NULL, 'line_items', 'items',                9),
  (NULL, 'line_items', 'detalle',              8),
  (NULL, 'line_items', 'filas_detalle',        7)
ON CONFLICT (tenant_id, canonical_field, alias) DO NOTHING;
