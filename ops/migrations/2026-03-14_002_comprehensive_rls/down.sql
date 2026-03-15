-- =====================================================
-- Rollback: Remove all tenant_isolation_policy RLS policies
-- =====================================================

BEGIN;

-- Core business
DROP POLICY IF EXISTS tenant_isolation_policy ON products;
ALTER TABLE products DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON product_categories;
ALTER TABLE product_categories DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON clients;
ALTER TABLE clients DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON suppliers;
ALTER TABLE suppliers DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON supplier_addresses;
ALTER TABLE supplier_addresses DISABLE ROW LEVEL SECURITY;

-- Sales & invoicing
DROP POLICY IF EXISTS tenant_isolation_policy ON sales_orders;
ALTER TABLE sales_orders DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON invoices;
ALTER TABLE invoices DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON invoice_lines;
ALTER TABLE invoice_lines DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON invoices_temp;
ALTER TABLE invoices_temp DISABLE ROW LEVEL SECURITY;

-- Purchases & expenses
DROP POLICY IF EXISTS tenant_isolation_policy ON purchases;
ALTER TABLE purchases DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON purchase_lines;
ALTER TABLE purchase_lines DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON expenses;
ALTER TABLE expenses DISABLE ROW LEVEL SECURITY;

-- Inventory
DROP POLICY IF EXISTS tenant_isolation_policy ON warehouses;
ALTER TABLE warehouses DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON stock_items;
ALTER TABLE stock_items DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON stock_moves;
ALTER TABLE stock_moves DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON stock_alerts;
ALTER TABLE stock_alerts DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_transfers DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON internal_transfers;
ALTER TABLE internal_transfers DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON inventory_settings;
ALTER TABLE inventory_settings DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON inventory_cost_layers;
DROP POLICY IF EXISTS tenant_isolation_policy ON inventory_cost_state;

-- POS
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_registers;
ALTER TABLE pos_registers DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_shifts;
ALTER TABLE pos_shifts DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_receipts;
ALTER TABLE pos_receipts DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_receipt_lines;
ALTER TABLE pos_receipt_lines DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_payments;
ALTER TABLE pos_payments DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON pos_daily_counts;

-- Finance & banking
DROP POLICY IF EXISTS tenant_isolation_policy ON bank_accounts;
ALTER TABLE bank_accounts DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON bank_transactions;
ALTER TABLE bank_transactions DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON bank_movements;
ALTER TABLE bank_movements DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON cash_closings;
ALTER TABLE cash_closings DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON cash_movements;
ALTER TABLE cash_movements DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON payments;
ALTER TABLE payments DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON store_credits;
ALTER TABLE store_credits DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON store_credit_events;
ALTER TABLE store_credit_events DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON journal_entries;

-- Production
DROP POLICY IF EXISTS tenant_isolation_policy ON recipes;
ALTER TABLE recipes DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON recipe_ingredients;
ALTER TABLE recipe_ingredients DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON production_orders;
ALTER TABLE production_orders DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON production_order_lines;
ALTER TABLE production_order_lines DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON production_cost_drivers;
DROP POLICY IF EXISTS tenant_isolation_policy ON daily_production_logs;

-- HR
DROP POLICY IF EXISTS tenant_isolation_policy ON employees;
ALTER TABLE employees DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON vacations;
ALTER TABLE vacations DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON payrolls;
ALTER TABLE payrolls DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON payroll_concepts;
ALTER TABLE payroll_concepts DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON payroll_templates;
ALTER TABLE payroll_templates DISABLE ROW LEVEL SECURITY;

-- E-invoicing
DROP POLICY IF EXISTS tenant_isolation_policy ON einv_credentials;
DROP POLICY IF EXISTS tenant_isolation_policy ON sri_submissions;
DROP POLICY IF EXISTS tenant_isolation_policy ON sii_batches;
DROP POLICY IF EXISTS tenant_isolation_policy ON sii_batch_items;
DROP POLICY IF EXISTS tenant_isolation_policy ON doc_series;
ALTER TABLE doc_series DISABLE ROW LEVEL SECURITY;

-- Config & users
DROP POLICY IF EXISTS tenant_isolation_policy ON company_settings;
ALTER TABLE company_settings DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON company_users;
ALTER TABLE company_users DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON company_user_roles;
ALTER TABLE company_user_roles DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON company_roles;
ALTER TABLE company_roles DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON company_modules;
ALTER TABLE company_modules DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON assigned_modules;
ALTER TABLE assigned_modules DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON user_profiles;
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;

-- Imports
DROP POLICY IF EXISTS tenant_isolation_policy ON import_batches;
DROP POLICY IF EXISTS tenant_isolation_policy ON import_items;
DROP POLICY IF EXISTS tenant_isolation_policy ON import_mappings;
DROP POLICY IF EXISTS tenant_isolation_policy ON import_ocr_jobs;
DROP POLICY IF EXISTS tenant_isolation_policy ON import_column_mappings;
ALTER TABLE import_column_mappings DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON import_audits;
ALTER TABLE import_audits DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON imp_documento;

-- CRM
DROP POLICY IF EXISTS tenant_isolation_policy ON crm_leads;
DROP POLICY IF EXISTS tenant_isolation_policy ON crm_opportunities;
DROP POLICY IF EXISTS tenant_isolation_policy ON crm_activities;

-- Audit & events
DROP POLICY IF EXISTS tenant_isolation_policy ON audit_events;
DROP POLICY IF EXISTS tenant_isolation_policy ON event_outbox;
DROP POLICY IF EXISTS tenant_isolation_policy ON incidents;
ALTER TABLE incidents DISABLE ROW LEVEL SECURITY;

-- Webhooks
DROP POLICY IF EXISTS tenant_isolation_policy ON webhook_subscriptions;
DROP POLICY IF EXISTS tenant_isolation_policy ON webhook_deliveries;

-- Documents & reports
DROP POLICY IF EXISTS tenant_isolation_policy ON documents;
DROP POLICY IF EXISTS tenant_isolation_policy ON profit_snapshots_daily;
DROP POLICY IF EXISTS tenant_isolation_policy ON notifications;

-- Auth
DROP POLICY IF EXISTS tenant_isolation_policy ON auth_audit;
ALTER TABLE auth_audit DISABLE ROW LEVEL SECURITY;

-- Misc
DROP POLICY IF EXISTS tenant_isolation_policy ON deliveries;
DROP POLICY IF EXISTS tenant_isolation_policy ON chart_of_accounts;
DROP POLICY IF EXISTS tenant_isolation_policy ON printer_label_configurations;
DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_field_configs;

COMMIT;
