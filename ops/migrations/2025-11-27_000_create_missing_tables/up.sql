-- Migration: 2025-11-27_000_create_missing_tables
-- Description: Create base tables required by later migrations.

BEGIN;

-- Ensure enum for chart_of_accounts exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_type WHERE typname = 'account_type'
    ) THEN
        CREATE TYPE account_type AS ENUM ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS tenant_field_configs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    module VARCHAR NOT NULL,
    field VARCHAR NOT NULL,
    visible BOOLEAN DEFAULT TRUE NOT NULL,
    required BOOLEAN DEFAULT FALSE NOT NULL,
    ord SMALLINT,
    label TEXT,
    help TEXT,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_field_configs_tenant_id
    ON tenant_field_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_field_configs_module
    ON tenant_field_configs(module);

CREATE TABLE IF NOT EXISTS import_batches (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type VARCHAR NOT NULL,
    origin VARCHAR NOT NULL,
    file_key VARCHAR,
    mapping_id UUID,
    parser_id VARCHAR,
    parser_choice_confidence VARCHAR,
    suggested_parser VARCHAR,
    classification_confidence DOUBLE PRECISION,
    ai_enhanced BOOLEAN DEFAULT FALSE NOT NULL,
    ai_provider VARCHAR,
    status VARCHAR DEFAULT 'PENDING',
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_import_batches_tenant_status_created
    ON import_batches(tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS ix_import_batches_ai_provider
    ON import_batches(ai_provider);
CREATE INDEX IF NOT EXISTS ix_import_batches_ai_enhanced
    ON import_batches(ai_enhanced);

CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type account_type NOT NULL,
    level INTEGER NOT NULL,
    parent_id UUID REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    can_post BOOLEAN DEFAULT TRUE NOT NULL,
    active BOOLEAN DEFAULT TRUE NOT NULL,
    debit_balance NUMERIC(14, 2) DEFAULT 0 NOT NULL,
    credit_balance NUMERIC(14, 2) DEFAULT 0 NOT NULL,
    balance NUMERIC(14, 2) DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_tenant_id
    ON chart_of_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_code
    ON chart_of_accounts(code);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_type
    ON chart_of_accounts(type);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_parent_id
    ON chart_of_accounts(parent_id);
CREATE INDEX IF NOT EXISTS ix_chart_of_accounts_active
    ON chart_of_accounts(active);

COMMIT;
