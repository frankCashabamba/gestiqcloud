-- Rename Spanish column names in hist_* tables to English.
BEGIN;

-- ── hist_sales ────────────────────────────────────────────────────────────────
ALTER TABLE hist_sales
    RENAME COLUMN fecha           TO date;
ALTER TABLE hist_sales
    RENAME COLUMN numero          TO number;
ALTER TABLE hist_sales
    RENAME COLUMN cliente_code    TO customer_code;
ALTER TABLE hist_sales
    RENAME COLUMN cliente_nombre  TO customer_name;
ALTER TABLE hist_sales
    RENAME COLUMN producto_code   TO product_code;
ALTER TABLE hist_sales
    RENAME COLUMN producto_nombre TO product_name;
ALTER TABLE hist_sales
    RENAME COLUMN cantidad        TO quantity;
ALTER TABLE hist_sales
    RENAME COLUMN precio_unitario TO unit_price;
ALTER TABLE hist_sales
    RENAME COLUMN impuesto        TO tax;
ALTER TABLE hist_sales
    RENAME COLUMN moneda          TO currency;

ALTER INDEX IF EXISTS ix_hist_sales_tenant_fecha RENAME TO ix_hist_sales_tenant_date;

-- ── hist_purchases ────────────────────────────────────────────────────────────
ALTER TABLE hist_purchases
    RENAME COLUMN fecha            TO date;
ALTER TABLE hist_purchases
    RENAME COLUMN numero           TO number;
ALTER TABLE hist_purchases
    RENAME COLUMN proveedor_code   TO supplier_code;
ALTER TABLE hist_purchases
    RENAME COLUMN proveedor_nombre TO supplier_name;
ALTER TABLE hist_purchases
    RENAME COLUMN producto_code    TO product_code;
ALTER TABLE hist_purchases
    RENAME COLUMN producto_nombre  TO product_name;
ALTER TABLE hist_purchases
    RENAME COLUMN cantidad         TO quantity;
ALTER TABLE hist_purchases
    RENAME COLUMN precio_unitario  TO unit_price;
ALTER TABLE hist_purchases
    RENAME COLUMN impuesto         TO tax;
ALTER TABLE hist_purchases
    RENAME COLUMN moneda           TO currency;

ALTER INDEX IF EXISTS ix_hist_purchases_tenant_fecha RENAME TO ix_hist_purchases_tenant_date;

-- ── hist_stock ────────────────────────────────────────────────────────────────
ALTER TABLE hist_stock
    RENAME COLUMN fecha           TO date;
ALTER TABLE hist_stock
    RENAME COLUMN producto_code   TO product_code;
ALTER TABLE hist_stock
    RENAME COLUMN producto_nombre TO product_name;
ALTER TABLE hist_stock
    RENAME COLUMN cantidad        TO quantity;
ALTER TABLE hist_stock
    RENAME COLUMN costo_unitario  TO unit_cost;
ALTER TABLE hist_stock
    RENAME COLUMN valor_total     TO total_value;
ALTER TABLE hist_stock
    RENAME COLUMN almacen         TO warehouse;

ALTER INDEX IF EXISTS ix_hist_stock_tenant_fecha RENAME TO ix_hist_stock_tenant_date;

-- ── hist_daily_sales ──────────────────────────────────────────────────────────
ALTER TABLE hist_daily_sales
    RENAME COLUMN fecha          TO date;
ALTER TABLE hist_daily_sales
    RENAME COLUMN total_ventas   TO sales_total;
ALTER TABLE hist_daily_sales
    RENAME COLUMN ticket_promedio TO avg_ticket;

ALTER INDEX IF EXISTS ix_hist_daily_sales_tenant_fecha RENAME TO ix_hist_daily_sales_tenant_date;

ALTER TABLE hist_daily_sales
    DROP CONSTRAINT IF EXISTS uq_hist_daily_sales_tenant_fecha;
ALTER TABLE hist_daily_sales
    ADD CONSTRAINT uq_hist_daily_sales_tenant_date UNIQUE (tenant_id, date);

COMMIT;
