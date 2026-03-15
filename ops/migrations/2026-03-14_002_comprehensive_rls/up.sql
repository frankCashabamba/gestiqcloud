-- =====================================================
-- Comprehensive RLS: enable tenant isolation on all
-- business tables with tenant_id column.
-- Policy: tenant_id = current_setting('app.tenant_id')
-- =====================================================

BEGIN;

-- Helper: idempotent policy creation
-- For each table: ENABLE RLS, FORCE RLS, CREATE POLICY

-- =====================================================
-- CORE BUSINESS TABLES (from consolidated schema)
-- =====================================================

-- products
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE products FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON products
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- product_categories
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_categories FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON product_categories
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- clients
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON clients
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- suppliers
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON suppliers
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- supplier_addresses (no tiene tenant_id — hereda aislamiento via suppliers parent)
DO $$ BEGIN
    ALTER TABLE supplier_addresses ENABLE ROW LEVEL SECURITY;
    ALTER TABLE supplier_addresses FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON supplier_addresses
        USING (supplier_id IN (
            SELECT id FROM suppliers
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- supplier_contacts (no tiene tenant_id — hereda aislamiento via suppliers parent)
DO $$ BEGIN
    ALTER TABLE supplier_contacts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE supplier_contacts FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON supplier_contacts
        USING (supplier_id IN (
            SELECT id FROM suppliers
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- SALES & INVOICING
-- =====================================================

-- sales_orders
ALTER TABLE sales_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_orders FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON sales_orders
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- sales_order_items (no tiene tenant_id — hereda aislamiento via sales_orders parent)
DO $$ BEGIN
    ALTER TABLE sales_order_items ENABLE ROW LEVEL SECURITY;
    ALTER TABLE sales_order_items FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON sales_order_items
        USING (sales_order_id IN (
            SELECT id FROM sales_orders
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- invoices
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON invoices
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- invoice_lines (no tiene tenant_id — hereda aislamiento via invoices parent)
DO $$ BEGIN
    ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY;
    ALTER TABLE invoice_lines FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON invoice_lines
        USING (invoice_id IN (
            SELECT id FROM invoices
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- invoices_temp
ALTER TABLE invoices_temp ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices_temp FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON invoices_temp
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- PURCHASES & EXPENSES
-- =====================================================

-- purchases
ALTER TABLE purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchases FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON purchases
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- purchase_lines (no tiene tenant_id — hereda aislamiento via purchases parent)
DO $$ BEGIN
    ALTER TABLE purchase_lines ENABLE ROW LEVEL SECURITY;
    ALTER TABLE purchase_lines FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON purchase_lines
        USING (purchase_id IN (
            SELECT id FROM purchases
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- expenses
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON expenses
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- INVENTORY
-- =====================================================

-- warehouses
ALTER TABLE warehouses ENABLE ROW LEVEL SECURITY;
ALTER TABLE warehouses FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON warehouses
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- stock_items
ALTER TABLE stock_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_items FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON stock_items
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- stock_moves
ALTER TABLE stock_moves ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_moves FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON stock_moves
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- stock_alerts
ALTER TABLE stock_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_alerts FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON stock_alerts
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- stock_transfers (may already have policy from 020_stock_transfers.sql)
ALTER TABLE stock_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_transfers FORCE ROW LEVEL SECURITY;

-- internal_transfers
ALTER TABLE internal_transfers ENABLE ROW LEVEL SECURITY;
ALTER TABLE internal_transfers FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON internal_transfers
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- inventory_settings
ALTER TABLE inventory_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_settings FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON inventory_settings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- inventory_cost_layers
DO $$ BEGIN
    ALTER TABLE inventory_cost_layers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE inventory_cost_layers FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON inventory_cost_layers
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- POS
-- =====================================================

-- pos_registers
ALTER TABLE pos_registers ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos_registers FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON pos_registers
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- pos_shifts (no tiene tenant_id — hereda aislamiento via pos_registers parent)
DO $$ BEGIN
    ALTER TABLE pos_shifts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE pos_shifts FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON pos_shifts
        USING (register_id IN (
            SELECT id FROM pos_registers
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- pos_receipts
ALTER TABLE pos_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pos_receipts FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON pos_receipts
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- pos_receipt_lines (no tiene tenant_id — hereda aislamiento via pos_receipts parent)
DO $$ BEGIN
    ALTER TABLE pos_receipt_lines ENABLE ROW LEVEL SECURITY;
    ALTER TABLE pos_receipt_lines FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON pos_receipt_lines
        USING (receipt_id IN (
            SELECT id FROM pos_receipts
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- pos_payments (no tiene tenant_id — hereda aislamiento via pos_receipts parent)
DO $$ BEGIN
    ALTER TABLE pos_payments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE pos_payments FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON pos_payments
        USING (receipt_id IN (
            SELECT id FROM pos_receipts
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- pos_daily_counts
DO $$ BEGIN
    ALTER TABLE pos_daily_counts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE pos_daily_counts FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON pos_daily_counts
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- FINANCE & BANKING
-- =====================================================

-- bank_accounts
ALTER TABLE bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_accounts FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON bank_accounts
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- bank_transactions
ALTER TABLE bank_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_transactions FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON bank_transactions
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- bank_movements
ALTER TABLE bank_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_movements FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON bank_movements
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- cash_closings
ALTER TABLE cash_closings ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_closings FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON cash_closings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- cash_movements
ALTER TABLE cash_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_movements FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON cash_movements
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON payments
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- store_credits
ALTER TABLE store_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE store_credits FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON store_credits
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- store_credit_events (no tiene tenant_id — hereda aislamiento via store_credits parent)
DO $$ BEGIN
    ALTER TABLE store_credit_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE store_credit_events FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON store_credit_events
        USING (credit_id IN (
            SELECT id FROM store_credits
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- journal_entries
DO $$ BEGIN
    ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE journal_entries FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON journal_entries
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- PRODUCTION
-- =====================================================

-- recipes
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipes FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON recipes
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- recipe_ingredients (no tiene tenant_id — hereda aislamiento via recipes parent)
DO $$ BEGIN
    ALTER TABLE recipe_ingredients ENABLE ROW LEVEL SECURITY;
    ALTER TABLE recipe_ingredients FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON recipe_ingredients
        USING (recipe_id IN (
            SELECT id FROM recipes
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- production_orders
ALTER TABLE production_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE production_orders FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON production_orders
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- production_order_lines (no tiene tenant_id — hereda aislamiento via production_orders parent)
DO $$ BEGIN
    ALTER TABLE production_order_lines ENABLE ROW LEVEL SECURITY;
    ALTER TABLE production_order_lines FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON production_order_lines
        USING (order_id IN (
            SELECT id FROM production_orders
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- production_cost_drivers
DO $$ BEGIN
    ALTER TABLE production_cost_drivers ENABLE ROW LEVEL SECURITY;
    ALTER TABLE production_cost_drivers FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON production_cost_drivers
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- daily_production_logs
DO $$ BEGIN
    ALTER TABLE daily_production_logs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE daily_production_logs FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON daily_production_logs
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- HR
-- =====================================================

-- employees
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON employees
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- vacations
ALTER TABLE vacations ENABLE ROW LEVEL SECURITY;
ALTER TABLE vacations FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON vacations
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- payrolls
ALTER TABLE payrolls ENABLE ROW LEVEL SECURITY;
ALTER TABLE payrolls FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON payrolls
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- payroll_concepts (no tiene tenant_id — hereda aislamiento via payrolls parent)
DO $$ BEGIN
    ALTER TABLE payroll_concepts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE payroll_concepts FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON payroll_concepts
        USING (payroll_id IN (
            SELECT id FROM payrolls
            WHERE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
        ));
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- payroll_templates
ALTER TABLE payroll_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_templates FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON payroll_templates
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- E-INVOICING
-- =====================================================

-- einv_credentials
DO $$ BEGIN
    ALTER TABLE einv_credentials ENABLE ROW LEVEL SECURITY;
    ALTER TABLE einv_credentials FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON einv_credentials
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- sri_submissions
DO $$ BEGIN
    ALTER TABLE sri_submissions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE sri_submissions FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON sri_submissions
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- sii_batches
DO $$ BEGIN
    ALTER TABLE sii_batches ENABLE ROW LEVEL SECURITY;
    ALTER TABLE sii_batches FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON sii_batches
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- sii_batch_items
DO $$ BEGIN
    ALTER TABLE sii_batch_items ENABLE ROW LEVEL SECURITY;
    ALTER TABLE sii_batch_items FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON sii_batch_items
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- doc_series
ALTER TABLE doc_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE doc_series FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON doc_series
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- TENANT CONFIG & USERS
-- =====================================================

-- company_settings
ALTER TABLE company_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_settings FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON company_settings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- company_users
ALTER TABLE company_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_users FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON company_users
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- company_user_roles
ALTER TABLE company_user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_user_roles FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON company_user_roles
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- company_roles
ALTER TABLE company_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_roles FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON company_roles
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- company_modules
ALTER TABLE company_modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_modules FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON company_modules
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- assigned_modules
ALTER TABLE assigned_modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE assigned_modules FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON assigned_modules
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- user_profiles
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON user_profiles
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- IMPORTS / OCR
-- =====================================================

-- import_batches
DO $$ BEGIN
    ALTER TABLE import_batches ENABLE ROW LEVEL SECURITY;
    ALTER TABLE import_batches FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON import_batches
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- import_items
DO $$ BEGIN
    ALTER TABLE import_items ENABLE ROW LEVEL SECURITY;
    ALTER TABLE import_items FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON import_items
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- import_mappings
DO $$ BEGIN
    ALTER TABLE import_mappings ENABLE ROW LEVEL SECURITY;
    ALTER TABLE import_mappings FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON import_mappings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- import_ocr_jobs
DO $$ BEGIN
    ALTER TABLE import_ocr_jobs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE import_ocr_jobs FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON import_ocr_jobs
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- import_column_mappings
ALTER TABLE import_column_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_column_mappings FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON import_column_mappings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- import_audits
ALTER TABLE import_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_audits FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON import_audits
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- imp_documento
DO $$ BEGIN
    ALTER TABLE imp_documento ENABLE ROW LEVEL SECURITY;
    ALTER TABLE imp_documento FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON imp_documento
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- CRM
-- =====================================================

-- crm_leads
DO $$ BEGIN
    ALTER TABLE crm_leads ENABLE ROW LEVEL SECURITY;
    ALTER TABLE crm_leads FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON crm_leads
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- crm_opportunities
DO $$ BEGIN
    ALTER TABLE crm_opportunities ENABLE ROW LEVEL SECURITY;
    ALTER TABLE crm_opportunities FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON crm_opportunities
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- crm_activities
DO $$ BEGIN
    ALTER TABLE crm_activities ENABLE ROW LEVEL SECURITY;
    ALTER TABLE crm_activities FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON crm_activities
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- AUDIT & EVENTS
-- =====================================================

-- audit_events
DO $$ BEGIN
    ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON audit_events
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- event_outbox
DO $$ BEGIN
    ALTER TABLE event_outbox ENABLE ROW LEVEL SECURITY;
    ALTER TABLE event_outbox FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON event_outbox
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- incidents
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE incidents FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON incidents
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- WEBHOOKS
-- =====================================================

-- webhook_subscriptions
DO $$ BEGIN
    ALTER TABLE webhook_subscriptions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE webhook_subscriptions FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON webhook_subscriptions
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- webhook_deliveries
DO $$ BEGIN
    ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE webhook_deliveries FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON webhook_deliveries
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- DOCUMENTS & REPORTS
-- =====================================================

-- documents
DO $$ BEGIN
    ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
    ALTER TABLE documents FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON documents
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- profit_snapshots_daily
DO $$ BEGIN
    ALTER TABLE profit_snapshots_daily ENABLE ROW LEVEL SECURITY;
    ALTER TABLE profit_snapshots_daily FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON profit_snapshots_daily
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- notifications
DO $$ BEGIN
    ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
    ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON notifications
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- =====================================================
-- AUTH (tenant-scoped)
-- =====================================================

-- auth_audit (tenant_id era VARCHAR — normalizar a UUID antes de habilitar RLS)
ALTER TABLE auth_audit
    ALTER COLUMN tenant_id TYPE UUID USING tenant_id::uuid;

ALTER TABLE auth_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit FORCE ROW LEVEL SECURITY;
DO $$ BEGIN
    CREATE POLICY tenant_isolation_policy ON auth_audit
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- MISC
-- =====================================================

-- deliveries
DO $$ BEGIN
    ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE deliveries FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON deliveries
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- chart_of_accounts
DO $$ BEGIN
    ALTER TABLE chart_of_accounts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE chart_of_accounts FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON chart_of_accounts
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- printer_label_configurations
DO $$ BEGIN
    ALTER TABLE printer_label_configurations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE printer_label_configurations FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON printer_label_configurations
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

-- tenant_field_configs
DO $$ BEGIN
    ALTER TABLE tenant_field_configs ENABLE ROW LEVEL SECURITY;
    ALTER TABLE tenant_field_configs FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation_policy ON tenant_field_configs
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
EXCEPTION WHEN duplicate_object THEN NULL;
         WHEN undefined_table THEN NULL;
END $$;

COMMIT;
