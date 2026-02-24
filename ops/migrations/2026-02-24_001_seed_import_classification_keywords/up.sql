-- Seed tenant_field_configs with classification keywords for ALL existing tenants.
-- This enables doc_type detection via DB without hardcoding.
-- Tenants can add/modify keywords via UPDATE/INSERT sin tocar código.

-- ============================================================
-- INVOICES (facturas)
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'invoice_number',
    '["factura", "invoice", "num. factura", "num factura", "nro factura", "numero factura", "folio", "comprobante", "nota de venta"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'invoice_number'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'client',
    '["cliente", "customer", "comprador", "destinatario", "buyer"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'client'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'tax',
    '["iva", "tax", "impuesto", "igv"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'tax'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'provider',
    '["proveedor", "supplier", "vendor", "emisor"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'provider'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'tax_id',
    '["ruc", "nif", "cif", "nit", "cedula", "identificacion"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'tax_id'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'amount',
    '["subtotal", "total", "total pagar", "importe", "monto"]'::jsonb,
    'number',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'amount'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_invoices', 'seller',
    '["vendedor", "seller", "cajero", "cashier", "forma de pago", "retencion"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_invoices' AND tfc.field = 'seller'
);

-- ============================================================
-- PRODUCTS (productos)
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_products', 'sku',
    '["sku", "codigo", "code", "barcode", "ean", "cod. producto"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_products' AND tfc.field = 'sku'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_products', 'name',
    '["producto", "product", "articulo", "nombre", "name", "descripcion"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_products' AND tfc.field = 'name'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_products', 'stock',
    '["stock", "existencias", "existencia", "inventario", "cantidad", "qty"]'::jsonb,
    'number',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_products' AND tfc.field = 'stock'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_products', 'price',
    '["precio", "price", "pvp", "precio_venta", "lista_precios", "catalogo"]'::jsonb,
    'number',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_products' AND tfc.field = 'price'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_products', 'category',
    '["categoria", "category", "tipo", "familia", "grupo"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_products' AND tfc.field = 'category'
);

-- ============================================================
-- BANK TRANSACTIONS (movimientos bancarios)
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_bank_transactions', 'account',
    '["iban", "cuenta", "account", "numero_cuenta"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_bank_transactions' AND tfc.field = 'account'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_bank_transactions', 'amount',
    '["saldo", "importe", "monto", "valor", "debit", "credit", "amount"]'::jsonb,
    'number',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_bank_transactions' AND tfc.field = 'amount'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_bank_transactions', 'concept',
    '["concepto", "description", "descripcion", "movimiento", "extracto", "transferencia"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_bank_transactions' AND tfc.field = 'concept'
);

INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_bank_transactions', 'bank',
    '["banco", "bank", "entidad", "transaction"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_bank_transactions' AND tfc.field = 'bank'
);

-- ============================================================
-- EXPENSES (gastos)
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_expenses', 'expense_type',
    '["gasto", "expense", "receipt", "recibo", "voucher", "compra", "egreso", "desembolso"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_expenses' AND tfc.field = 'expense_type'
);

-- ============================================================
-- RECIPES (recetas/costeo)
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_recipes', 'recipe_name',
    '["ingredientes", "costo total ingredientes", "formato de costeo", "receta", "recipe", "porciones", "temperatura de servicio", "preparacion"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_recipes' AND tfc.field = 'recipe_name'
);

-- ============================================================
-- TICKET POS
-- ============================================================
INSERT INTO tenant_field_configs (id, tenant_id, module, field, aliases, field_type, visible, required)
SELECT
    gen_random_uuid(), t.id, 'imports_ticket_pos', 'ticket_number',
    '["ticket de venta", "ticket venta", "nota de venta", "comprobante de venta", "boleta de venta"]'::jsonb,
    'string',
    true, false
FROM tenants t
WHERE NOT EXISTS (
    SELECT 1 FROM tenant_field_configs tfc
    WHERE tfc.tenant_id = t.id AND tfc.module = 'imports_ticket_pos' AND tfc.field = 'ticket_number'
);
