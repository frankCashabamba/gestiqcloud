-- Revert English column renames back to Spanish.
BEGIN;

-- ── hist_sales ────────────────────────────────────────────────────────────────
ALTER TABLE hist_sales RENAME COLUMN date          TO fecha;
ALTER TABLE hist_sales RENAME COLUMN number        TO numero;
ALTER TABLE hist_sales RENAME COLUMN customer_code TO cliente_code;
ALTER TABLE hist_sales RENAME COLUMN customer_name TO cliente_nombre;
ALTER TABLE hist_sales RENAME COLUMN product_code  TO producto_code;
ALTER TABLE hist_sales RENAME COLUMN product_name  TO producto_nombre;
ALTER TABLE hist_sales RENAME COLUMN quantity      TO cantidad;
ALTER TABLE hist_sales RENAME COLUMN unit_price    TO precio_unitario;
ALTER TABLE hist_sales RENAME COLUMN tax           TO impuesto;
ALTER TABLE hist_sales RENAME COLUMN currency      TO moneda;
ALTER INDEX IF EXISTS ix_hist_sales_tenant_date RENAME TO ix_hist_sales_tenant_fecha;

-- ── hist_purchases ────────────────────────────────────────────────────────────
ALTER TABLE hist_purchases RENAME COLUMN date          TO fecha;
ALTER TABLE hist_purchases RENAME COLUMN number        TO numero;
ALTER TABLE hist_purchases RENAME COLUMN supplier_code TO proveedor_code;
ALTER TABLE hist_purchases RENAME COLUMN supplier_name TO proveedor_nombre;
ALTER TABLE hist_purchases RENAME COLUMN product_code  TO producto_code;
ALTER TABLE hist_purchases RENAME COLUMN product_name  TO producto_nombre;
ALTER TABLE hist_purchases RENAME COLUMN quantity      TO cantidad;
ALTER TABLE hist_purchases RENAME COLUMN unit_price    TO precio_unitario;
ALTER TABLE hist_purchases RENAME COLUMN tax           TO impuesto;
ALTER TABLE hist_purchases RENAME COLUMN currency      TO moneda;
ALTER INDEX IF EXISTS ix_hist_purchases_tenant_date RENAME TO ix_hist_purchases_tenant_fecha;

-- ── hist_stock ────────────────────────────────────────────────────────────────
ALTER TABLE hist_stock RENAME COLUMN date         TO fecha;
ALTER TABLE hist_stock RENAME COLUMN product_code TO producto_code;
ALTER TABLE hist_stock RENAME COLUMN product_name TO producto_nombre;
ALTER TABLE hist_stock RENAME COLUMN quantity     TO cantidad;
ALTER TABLE hist_stock RENAME COLUMN unit_cost    TO costo_unitario;
ALTER TABLE hist_stock RENAME COLUMN total_value  TO valor_total;
ALTER TABLE hist_stock RENAME COLUMN warehouse    TO almacen;
ALTER INDEX IF EXISTS ix_hist_stock_tenant_date RENAME TO ix_hist_stock_tenant_fecha;

-- ── hist_daily_sales ──────────────────────────────────────────────────────────
ALTER TABLE hist_daily_sales RENAME COLUMN date        TO fecha;
ALTER TABLE hist_daily_sales RENAME COLUMN sales_total TO total_ventas;
ALTER TABLE hist_daily_sales RENAME COLUMN avg_ticket  TO ticket_promedio;
ALTER INDEX IF EXISTS ix_hist_daily_sales_tenant_date RENAME TO ix_hist_daily_sales_tenant_fecha;
ALTER TABLE hist_daily_sales DROP CONSTRAINT IF EXISTS uq_hist_daily_sales_tenant_date;
ALTER TABLE hist_daily_sales ADD CONSTRAINT uq_hist_daily_sales_tenant_fecha UNIQUE (tenant_id, fecha);

COMMIT;
