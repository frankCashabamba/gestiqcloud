-- Tabla que define los campos canónicos del sistema importador.
-- Elimina cualquier hardcoding de nombres de campo, tipos y proyecciones del código Python.
-- El código itera dinámicamente sobre esta tabla sin nombrar ningún campo explícitamente.

CREATE TABLE IF NOT EXISTS imp_canonical_field (
    name              VARCHAR(50)  PRIMARY KEY,
    field_type        VARCHAR(20)  NOT NULL DEFAULT 'text',
    -- text | numeric | date | payment_method | list
    projection_column VARCHAR(80),
    -- columna de ImpDocumento donde proyectar este valor (NULL = no proyectar)
    sort_order        INTEGER      NOT NULL DEFAULT 0,
    active            BOOLEAN      NOT NULL DEFAULT TRUE
);

-- Seed: todos los campos canónicos del sistema
INSERT INTO imp_canonical_field (name, field_type, projection_column, sort_order) VALUES
  ('vendor',          'text',           'proveedor_detectado',  10),
  ('vendor_tax_id',   'text',           'ruc_detectado',        9),
  ('total_amount',    'numeric',        'monto_total',          8),
  ('currency',        'text',           'moneda',               7),
  ('issue_date',      'date',           'fecha_documento',      6),
  ('subtotal',        'numeric',        NULL,                   5),
  ('tax_amount',      'numeric',        NULL,                   4),
  ('customer',        'text',           NULL,                   3),
  ('customer_tax_id', 'text',           NULL,                   2),
  ('doc_number',      'text',           NULL,                   15),
  ('payment_method',  'payment_method', NULL,                   14),
  ('payment_terms',   'text',           NULL,                   13),
  ('line_items',      'list',           NULL,                   12),
  ('concept',         'text',           NULL,                   11),
  ('category',        'text',           NULL,                   1)
ON CONFLICT (name) DO NOTHING;
