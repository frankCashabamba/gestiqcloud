-- Rollback: 2026-04-06_000_historical_module
BEGIN;

DROP POLICY IF EXISTS hist_daily_sales_tenant_isolation ON hist_daily_sales;
DROP TABLE IF EXISTS hist_daily_sales;

DROP POLICY IF EXISTS hist_stock_tenant_isolation ON hist_stock;
DROP TABLE IF EXISTS hist_stock;

DROP POLICY IF EXISTS hist_purchases_tenant_isolation ON hist_purchases;
DROP TABLE IF EXISTS hist_purchases;

DROP POLICY IF EXISTS hist_sales_tenant_isolation ON hist_sales;
DROP TABLE IF EXISTS hist_sales;

DROP POLICY IF EXISTS hist_masters_tenant_isolation ON hist_masters;
DROP TABLE IF EXISTS hist_masters;

DROP POLICY IF EXISTS hist_imports_tenant_isolation ON hist_imports;
DROP TABLE IF EXISTS hist_imports;

COMMIT;
