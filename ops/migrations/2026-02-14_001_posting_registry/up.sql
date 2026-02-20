-- Migration: 2026-02-14_001_posting_registry
-- Description: Import Resolutions + Posting Registry for idempotency

BEGIN;

-- import_resolutions: Persistir mappings sugeridos (ej: "PAN TAPADO" → producto 123)
CREATE TABLE IF NOT EXISTS import_resolutions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_job_id UUID REFERENCES import_batches(id) ON DELETE SET NULL,
    entity_type TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    resolved_id UUID,
    status TEXT NOT NULL DEFAULT 'pending',
    confidence NUMERIC(3,2),
    resolved_by TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_import_res_job_entity_raw UNIQUE (import_job_id, entity_type, raw_value)
);

CREATE INDEX IF NOT EXISTS ix_import_resolutions_tenant_id ON import_resolutions(tenant_id);
CREATE INDEX IF NOT EXISTS ix_import_resolutions_tenant_entity_raw ON import_resolutions(tenant_id, entity_type, raw_value);

-- posting_registry: Idempotencia — evita duplicados al reimportar
CREATE TABLE IF NOT EXISTS posting_registry (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    import_job_id UUID REFERENCES import_batches(id) ON DELETE SET NULL,
    posting_key TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_posting_registry_tenant_key UNIQUE (tenant_id, posting_key)
);

CREATE INDEX IF NOT EXISTS ix_posting_registry_tenant_id ON posting_registry(tenant_id);
CREATE INDEX IF NOT EXISTS ix_posting_registry_tenant_key ON posting_registry(tenant_id, posting_key);
CREATE INDEX IF NOT EXISTS ix_posting_registry_import_job ON posting_registry(import_job_id);

COMMIT;
