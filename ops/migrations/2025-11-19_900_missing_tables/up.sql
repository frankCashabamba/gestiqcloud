-- =====================================================
-- Migration: 2025-11-19_900_missing_tables
-- Description: Create remaining missing tables from models
-- =====================================================

BEGIN;

-- =====================================================
-- 1. modules, company_modules, assigned_modules
-- =====================================================

CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    icon VARCHAR(100) DEFAULT 'package',
    url VARCHAR(255),
    initial_template VARCHAR(255) NOT NULL,
    context_type VARCHAR(10) DEFAULT 'none',
    target_model VARCHAR(255),
    context_filters JSONB,
    category VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS company_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    active BOOLEAN DEFAULT TRUE,
    activation_date DATE DEFAULT CURRENT_DATE,
    expiration_date DATE,
    initial_template VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS assigned_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES company_users(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    assignment_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    auto_view_module BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, module_id, tenant_id)
);

-- =====================================================
-- 2. Language, Currency, Country catalogs
-- =====================================================

CREATE TABLE IF NOT EXISTS languages (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS currencies (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(5) NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- 3. Weekday and BusinessHours
-- =====================================================

CREATE TABLE IF NOT EXISTS weekdays (
    id SERIAL PRIMARY KEY,
    key VARCHAR(20) UNIQUE,
    name VARCHAR(50),
    "order" INTEGER
);

CREATE TABLE IF NOT EXISTS business_hours (
    id SERIAL PRIMARY KEY,
    weekday_id INTEGER REFERENCES weekdays(id) ON DELETE CASCADE,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL
);

-- =====================================================
-- 4. Company/Tenant Settings
-- =====================================================

CREATE TABLE IF NOT EXISTS company_settings (
    id SERIAL PRIMARY KEY,
    tenant_id UUID UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    default_language VARCHAR(10) DEFAULT 'es',
    timezone VARCHAR(50) DEFAULT 'UTC',
    currency VARCHAR(10) DEFAULT 'USD',
    company_logo VARCHAR(100),
    secondary_color VARCHAR(7) DEFAULT '#6c757d',
    primary_color VARCHAR(7) DEFAULT '#4f46e5',
    allow_custom_roles BOOLEAN DEFAULT TRUE,
    user_limit INTEGER DEFAULT 10,
    working_days JSONB DEFAULT '["lunes","martes","miércoles","jueves","viernes"]'::jsonb,
    business_hours JSONB DEFAULT '{"start":"09:00","end":"18:00"}'::jsonb,
    operation_type VARCHAR DEFAULT 'ventas',
    company_name VARCHAR,
    tax_id VARCHAR,
    tax_regime VARCHAR,
    language_id INTEGER REFERENCES languages(id),
    currency_id INTEGER REFERENCES currencies(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory_settings (
    id SERIAL PRIMARY KEY,
    tenant_id UUID UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    stock_control_enabled BOOLEAN DEFAULT TRUE,
    low_stock_notification_enabled BOOLEAN DEFAULT TRUE,
    global_minimum_stock INTEGER,
    default_units JSONB,
    custom_categories_enabled BOOLEAN DEFAULT FALSE,
    extra_product_fields JSONB
);

-- =====================================================
-- 5. Accounting: Chart of Accounts
-- =====================================================

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    level INTEGER NOT NULL,
    parent_id UUID REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    can_post BOOLEAN DEFAULT FALSE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

-- =====================================================
-- 6. Banking: Accounts, Transactions, Payments
-- =====================================================

CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    iban VARCHAR,
    bank VARCHAR,
    currency VARCHAR DEFAULT 'EUR',
    customer_id UUID REFERENCES clients(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES bank_accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    amount FLOAT NOT NULL,
    currency VARCHAR DEFAULT 'EUR',
    type VARCHAR,
    status VARCHAR DEFAULT 'pending',
    concept VARCHAR,
    reference VARCHAR,
    counterparty_name VARCHAR,
    counterparty_iban VARCHAR,
    counterparty_bank VARCHAR,
    commission FLOAT DEFAULT 0,
    source VARCHAR DEFAULT 'ocr',
    attachment_url VARCHAR,
    sepa_end_to_end_id VARCHAR,
    sepa_creditor_id VARCHAR,
    sepa_mandate_ref VARCHAR,
    sepa_scheme VARCHAR,
    customer_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    category VARCHAR(100),
    origin VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    bank_tx_id UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    date DATE,
    applied_amount FLOAT,
    notes VARCHAR
);

CREATE TABLE IF NOT EXISTS internal_transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    source_tx_id UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    destination_tx_id UUID NOT NULL REFERENCES bank_transactions(id) ON DELETE CASCADE,
    exchange_rate FLOAT DEFAULT 1.0
);

-- =====================================================
-- 7. Invoices: Temp and related
-- =====================================================

CREATE TABLE IF NOT EXISTS invoices_temp (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES company_users(id),
    file_name VARCHAR,
    data JSONB,
    status VARCHAR DEFAULT 'pending',
    import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE
);

-- =====================================================
-- 8. Imports: Attachments, Audits, Lineage
-- =====================================================

CREATE TABLE IF NOT EXISTS import_attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID,
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    kind VARCHAR NOT NULL,
    file_key VARCHAR NOT NULL,
    sha256 VARCHAR,
    ocr_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    batch_id UUID REFERENCES import_batches(id) ON DELETE CASCADE,
    action VARCHAR NOT NULL,
    actor_id VARCHAR,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_lineages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    promoted_to VARCHAR NOT NULL,
    promoted_ref VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 9. Global Settings and Permissions
-- =====================================================

CREATE TABLE IF NOT EXISTS global_action_permissions (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE,
    description VARCHAR(100)
);

-- =====================================================
-- 10. Sector Templates
-- =====================================================

CREATE TABLE IF NOT EXISTS sector_templates (
    id SERIAL PRIMARY KEY,
    sector_name VARCHAR(100) UNIQUE NOT NULL,
    business_type_id INTEGER REFERENCES business_types(id),
    business_category_id INTEGER REFERENCES business_categories(id),
    template_config JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- Create indexes for performance
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_modules_name ON modules(name);
CREATE INDEX IF NOT EXISTS idx_company_modules_tenant ON company_modules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_assigned_modules_user ON assigned_modules(user_id);
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_tenant_code ON chart_of_accounts(tenant_id, code);
CREATE INDEX IF NOT EXISTS idx_chart_of_accounts_type ON chart_of_accounts(type);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_tenant ON bank_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON bank_transactions(date);
CREATE INDEX IF NOT EXISTS idx_payments_tenant ON payments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_import_attachments_item ON import_attachments(item_id);
CREATE INDEX IF NOT EXISTS idx_import_audits_tenant ON import_audits(tenant_id);
CREATE INDEX IF NOT EXISTS idx_import_lineages_item ON import_lineages(item_id);
CREATE INDEX IF NOT EXISTS idx_company_settings_tenant ON company_settings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_inventory_settings_tenant ON inventory_settings(tenant_id);

COMMIT;
