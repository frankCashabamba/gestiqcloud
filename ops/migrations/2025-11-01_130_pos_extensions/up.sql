-- =====================================================
-- POS EXTENSIONS: Store Credits, Store Credit Events
-- Migration: 2025-11-01_130_pos_extensions
-- =====================================================

BEGIN;

-- =====================================================
-- STORE_CREDITS: Store Credit Vouchers
-- =====================================================
CREATE TABLE IF NOT EXISTS store_credits (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    customer_id UUID,
    currency VARCHAR(3) NOT NULL,
    amount_initial NUMERIC(12, 2) NOT NULL,
    amount_remaining NUMERIC(12, 2) NOT NULL,
    expires_at DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES clients(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_store_credits_id ON store_credits(id);
CREATE INDEX IF NOT EXISTS idx_store_credits_tenant_id ON store_credits(tenant_id);
CREATE INDEX IF NOT EXISTS idx_store_credits_code ON store_credits(code);

-- =====================================================
-- STORE_CREDIT_EVENTS: Store Credit Transaction History
-- =====================================================
CREATE TABLE IF NOT EXISTS store_credit_events (
    id UUID DEFAULT gen_random_uuid(),
    credit_id UUID NOT NULL,
    type VARCHAR(20) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    ref_doc_type VARCHAR(50),
    ref_doc_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (credit_id) REFERENCES store_credits(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_store_credit_events_credit_id ON store_credit_events(credit_id);

COMMIT;
