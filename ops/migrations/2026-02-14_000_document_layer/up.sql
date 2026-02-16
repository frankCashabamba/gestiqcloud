-- Migration: 2026-02-14_000_document_layer
-- Description: Document Layer — WORM file storage with SHA256 dedupe + versionado

BEGIN;

-- document_files: Registro centralizado de archivos subidos
CREATE TABLE IF NOT EXISTS document_files (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by UUID NOT NULL,
    source TEXT,
    doc_type TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    tags JSONB,
    metadata_ JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_document_files_tenant_id ON document_files(tenant_id);
CREATE INDEX IF NOT EXISTS ix_document_files_tenant_doc_type ON document_files(tenant_id, doc_type);
CREATE INDEX IF NOT EXISTS ix_document_files_tenant_status ON document_files(tenant_id, status);

-- document_versions: Versionado WORM con SHA256 dedupe
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL,
    document_id UUID NOT NULL REFERENCES document_files(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    file_name TEXT,
    mime TEXT,
    size BIGINT,
    sha256 VARCHAR(64) NOT NULL,
    storage_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_docver_tenant_sha256 UNIQUE (tenant_id, sha256),
    CONSTRAINT uq_docver_doc_version UNIQUE (document_id, version)
);

CREATE INDEX IF NOT EXISTS ix_docver_tenant_sha256 ON document_versions(tenant_id, sha256);
CREATE INDEX IF NOT EXISTS ix_docver_doc_version_desc ON document_versions(document_id, version DESC);

-- Vincular import_batches con document_versions
ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS document_version_id UUID REFERENCES document_versions(id) ON DELETE SET NULL;
ALTER TABLE import_batches ADD COLUMN IF NOT EXISTS stats JSONB DEFAULT '{}';

COMMIT;
