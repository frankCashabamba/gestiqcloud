-- Rollback: 2025-11-18_310_sales_system

BEGIN;

DROP TRIGGER IF EXISTS deliveries_updated_at ON deliveries;
DROP TRIGGER IF EXISTS sales_updated_at ON sales;
DROP TRIGGER IF EXISTS sales_orders_updated_at ON sales_orders;

DROP POLICY IF EXISTS tenant_isolation_deliveries ON deliveries;
DROP POLICY IF EXISTS tenant_isolation_sales ON sales;
DROP POLICY IF EXISTS tenant_isolation_sales_orders ON sales_orders;

DROP TABLE IF EXISTS deliveries CASCADE;
DROP TABLE IF EXISTS sales_order_items CASCADE;
DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;

DROP TYPE IF EXISTS delivery_status CASCADE;
DROP TYPE IF EXISTS sales_order_status CASCADE;

DROP FUNCTION IF EXISTS update_updated_at_column();

COMMIT;
