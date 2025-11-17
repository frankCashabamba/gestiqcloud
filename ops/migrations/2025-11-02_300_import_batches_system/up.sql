-- Migration: Create import_batches and import_items tables
-- Date: 2025-11-02
-- Description: Modern batch/item import system (replaces legacy datos_importados)

-- Import Batches (parent container)
CREATE TABLE IF NOT EXISTS import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'productos'|'invoices'|'bank'|'receipts'
    origin VARCHAR(255) NOT NULL,     -- filename or source identifier
    file_key VARCHAR(500),            -- S3/MinIO path (optional)
    mapping_id UUID,                  -- FK to import_mappings (optional)
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING|PARSING|READY|VALIDATED|PARTIAL|ERROR|PROMOTED
    created_by VARCHAR(100) NOT NULL, -- user_id (string for SQLite compatibility)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_import_batches_tenant_status_created
    ON import_batches(tenant_id, status, created_at);

-- Import Items (individual rows within batch)
CREATE TABLE IF NOT EXISTS import_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    batch_id UUID NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,                  -- row index within file/batch
    raw JSONB NOT NULL,                    -- raw data as received
    normalized JSONB,                      -- after mapping/transforms applied
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING|OK|ERROR_VALIDATION|ERROR_PROMOTION|PROMOTED
    errors JSONB DEFAULT '[]'::jsonb,      -- [{field, message}]
    dedupe_hash VARCHAR(64),               -- sha256(...)
    idempotency_key VARCHAR(200),          -- tenant+file+idx or custom key
    promoted_to VARCHAR(50),               -- 'invoices'|'products'|'bank_txn'
    promoted_id UUID,                      -- FK to promoted entity
    promoted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint for idempotency (only when idempotency_key is not null)
CREATE UNIQUE INDEX IF NOT EXISTS uq_import_items_batch_idem
    ON import_items(batch_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Also keep tenant-level uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS uq_import_items_tenant_idem
    ON import_items(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_import_items_tenant_dedupe
    ON import_items(tenant_id, dedupe_hash);

CREATE INDEX IF NOT EXISTS ix_import_items_batch_id
    ON import_items(batch_id);

CREATE INDEX IF NOT EXISTS ix_import_items_normalized_gin
    ON import_items USING gin(normalized);

CREATE INDEX IF NOT EXISTS ix_import_items_raw_gin
    ON import_items USING gin(raw);

-- Conditional index for doc_type searches
CREATE INDEX IF NOT EXISTS ix_import_items_doc_type
    ON import_items((normalized->>'doc_type'))
    WHERE normalized ? 'doc_type';

-- Import Mappings (reusable templates)
CREATE TABLE IF NOT EXISTS import_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- 'productos'|'invoices'|'bank'
    version INTEGER NOT NULL DEFAULT 1,
    mappings JSONB,    -- {'dest_field': 'src_field'}
    transforms JSONB,  -- {'field': 'date'} or complex transforms
    defaults JSONB,    -- {'field': default_value}
    dedupe_keys JSONB, -- ['tax_id','invoice_number',...]
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_import_mappings_tenant_source
    ON import_mappings(tenant_id, source_type);

CREATE INDEX IF NOT EXISTS ix_import_mappings_mappings_gin
    ON import_mappings USING gin(mappings);

-- Import Item Corrections (audit trail)
CREATE TABLE IF NOT EXISTS import_item_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    field VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_import_item_corrections_item_id
    ON import_item_corrections(item_id);

-- Import Lineage (track promotions)
CREATE TABLE IF NOT EXISTS import_lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    promoted_to VARCHAR(50) NOT NULL, -- 'invoices'|'products'|'bank'
    promoted_ref VARCHAR(255),        -- domain identifier (string)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_import_lineage_item_id
    ON import_lineage(item_id);

-- Import OCR Jobs
CREATE TABLE IF NOT EXISTS import_ocr_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    content_type VARCHAR(100),
    payload BYTEA NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending'|'processing'|'completed'|'failed'
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_status_created
    ON import_ocr_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_tenant_status_created
    ON import_ocr_jobs(tenant_id, status, created_at);

-- RLS Policies (multi-tenant isolation)
ALTER TABLE import_batches ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_item_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_lineage ENABLE ROW LEVEL SECURITY;
ALTER TABLE import_ocr_jobs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS tenant_isolation ON import_batches;
DROP POLICY IF EXISTS tenant_isolation ON import_items;
DROP POLICY IF EXISTS tenant_isolation ON import_mappings;
DROP POLICY IF EXISTS tenant_isolation ON import_item_corrections;
DROP POLICY IF EXISTS tenant_isolation ON import_lineage;
DROP POLICY IF EXISTS tenant_isolation ON import_ocr_jobs;

-- Create RLS policies
CREATE POLICY tenant_isolation ON import_batches
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation ON import_items
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation ON import_mappings
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation ON import_item_corrections
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation ON import_lineage
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

CREATE POLICY tenant_isolation ON import_ocr_jobs
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));
