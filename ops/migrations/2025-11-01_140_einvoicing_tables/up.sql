-- =====================================================
-- E-INVOICING TABLES: SRI (Ecuador) and SII (Spain)
-- Migration: 2025-11-01_140_einvoicing_tables
-- =====================================================

BEGIN;

-- =====================================================
-- CREATE ENUM TYPES
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sri_status') THEN
        CREATE TYPE sri_status AS ENUM (
            'PENDING', 'SENT', 'RECEIVED', 'AUTHORIZED', 'REJECTED', 'ERROR'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sii_batch_status') THEN
        CREATE TYPE sii_batch_status AS ENUM (
            'PENDING', 'SENT', 'ACCEPTED', 'PARTIAL', 'REJECTED', 'ERROR'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sii_item_status') THEN
        CREATE TYPE sii_item_status AS ENUM (
            'PENDING', 'SENT', 'ACCEPTED', 'REJECTED', 'ERROR'
        );
    END IF;
END $$;

-- =====================================================
-- EINV_CREDENTIALS: E-Invoicing Credentials
-- =====================================================
CREATE TABLE IF NOT EXISTS einv_credentials (
    id SERIAL,
    tenant_id UUID NOT NULL,
    country VARCHAR(2) NOT NULL,
    sri_cert_ref TEXT,
    sri_key_ref TEXT,
    sri_env VARCHAR(20),
    sii_agency TEXT,
    sii_cert_ref TEXT,
    sii_key_ref TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_einv_credentials_tenant_id ON einv_credentials(tenant_id);

-- =====================================================
-- SRI_SUBMISSIONS: Ecuador SRI Submissions
-- =====================================================
CREATE TABLE IF NOT EXISTS sri_submissions (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    status sri_status NOT NULL DEFAULT 'PENDING',
    error_code TEXT,
    error_message TEXT,
    receipt_number TEXT,
    authorization_number TEXT,
    payload TEXT,
    response TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_sri_submissions_tenant_id ON sri_submissions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sri_submissions_invoice_id ON sri_submissions(invoice_id);

-- =====================================================
-- SII_BATCHES: Spain SII Batches
-- =====================================================
CREATE TABLE IF NOT EXISTS sii_batches (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    period VARCHAR(10) NOT NULL,
    status sii_batch_status NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_sii_batches_tenant_id ON sii_batches(tenant_id);

-- =====================================================
-- SII_BATCH_ITEMS: SII Batch Line Items
-- =====================================================
CREATE TABLE IF NOT EXISTS sii_batch_items (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    batch_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    status sii_item_status NOT NULL DEFAULT 'PENDING',
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (batch_id) REFERENCES sii_batches(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sii_batch_items_tenant_id ON sii_batch_items(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sii_batch_items_batch_id ON sii_batch_items(batch_id);

COMMIT;
