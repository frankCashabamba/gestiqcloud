-- Migration: 2025-12-23_000_imports_tables
-- Description: Create imports module tables (items, mappings, attachments, corrections, lineage, ocr jobs).

BEGIN;

CREATE TABLE IF NOT EXISTS import_items (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID,
    batch_id UUID NOT NULL REFERENCES import_batches(id),
    idx INTEGER NOT NULL,
    raw JSONB NOT NULL,
    normalized JSONB,
    canonical_doc JSONB,
    status VARCHAR DEFAULT 'PENDING',
    errors JSONB,
    dedupe_hash VARCHAR,
    idempotency_key VARCHAR,
    promoted_to VARCHAR,
    promoted_id UUID,
    promoted_at TIMESTAMPTZ,
    PRIMARY KEY (id),
    CONSTRAINT uq_import_items_tenant_idem UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS import_attachments (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID,
    item_id UUID NOT NULL REFERENCES import_items(id),
    kind VARCHAR NOT NULL,
    file_key VARCHAR NOT NULL,
    sha256 VARCHAR,
    ocr_text TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS import_mappings (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR NOT NULL,
    source_type VARCHAR NOT NULL,
    version INTEGER DEFAULT 1,
    mappings JSONB,
    transforms JSONB,
    defaults JSONB,
    dedupe_keys JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS import_item_corrections (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES import_items(id),
    user_id UUID NOT NULL,
    field VARCHAR NOT NULL,
    old_value JSON,
    new_value JSON,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS import_lineage (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES import_items(id),
    promoted_to VARCHAR NOT NULL,
    promoted_ref VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS import_ocr_jobs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR NOT NULL,
    content_type VARCHAR,
    payload BYTEA NOT NULL,
    status VARCHAR DEFAULT 'pending' NOT NULL,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_import_items_tenant_id
    ON import_items(tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_items_batch_id
    ON import_items(batch_id);
CREATE INDEX IF NOT EXISTS ix_import_items_idempotency_key
    ON import_items(idempotency_key);
CREATE INDEX IF NOT EXISTS ix_import_items_tenant_dedupe
    ON import_items(tenant_id, dedupe_hash);
CREATE INDEX IF NOT EXISTS ix_import_items_normalized_gin
    ON import_items USING gin (normalized);
CREATE INDEX IF NOT EXISTS ix_import_items_raw_gin
    ON import_items USING gin (raw);
CREATE INDEX IF NOT EXISTS ix_import_items_doc_type
    ON import_items ((normalized->>'doc_type'))
    WHERE normalized ? 'doc_type';

CREATE INDEX IF NOT EXISTS ix_import_attachments_item_id
    ON import_attachments(item_id);
CREATE INDEX IF NOT EXISTS ix_import_attachments_tenant_id
    ON import_attachments(tenant_id);

CREATE INDEX IF NOT EXISTS ix_import_mappings_tenant_id
    ON import_mappings(tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_mappings_tenant_source
    ON import_mappings(tenant_id, source_type);
CREATE INDEX IF NOT EXISTS ix_import_mappings_mappings_gin
    ON import_mappings USING gin (mappings);

CREATE INDEX IF NOT EXISTS ix_import_item_corrections_item_id
    ON import_item_corrections(item_id);
CREATE INDEX IF NOT EXISTS ix_import_item_corrections_tenant_id
    ON import_item_corrections(tenant_id);

CREATE INDEX IF NOT EXISTS ix_import_lineage_item_id
    ON import_lineage(item_id);
CREATE INDEX IF NOT EXISTS ix_import_lineage_tenant_id
    ON import_lineage(tenant_id);

CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_tenant_id
    ON import_ocr_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_status_created
    ON import_ocr_jobs(status, created_at);
CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_tenant_status_created
    ON import_ocr_jobs(tenant_id, status, created_at);

COMMIT;
