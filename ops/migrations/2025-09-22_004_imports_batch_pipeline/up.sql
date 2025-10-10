-- Imports pipeline schema (PostgreSQL)

-- Enable extensions if needed (optional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS import_batches (
    id UUID PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES core_empresa(id),
    source_type TEXT NOT NULL,
    origin TEXT NOT NULL,
    file_key TEXT NULL,
    mapping_id UUID NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_items (
    id UUID PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    raw JSONB NOT NULL,
    normalized JSONB NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    errors JSONB NULL,
    dedupe_hash TEXT NULL,
    idempotency_key TEXT NOT NULL,
    promoted_to TEXT NULL,
    promoted_id UUID NULL,
    promoted_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_import_item_idem ON import_items(idempotency_key);
CREATE INDEX IF NOT EXISTS ix_import_items_batch ON import_items(batch_id);
CREATE INDEX IF NOT EXISTS ix_import_items_dedupe ON import_items(dedupe_hash);

CREATE TABLE IF NOT EXISTS import_mappings (
    id UUID PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES core_empresa(id),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    mappings JSONB NULL,
    transforms JSONB NULL,
    defaults JSONB NULL,
    dedupe_keys JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_item_corrections (
    id UUID PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES core_empresa(id),
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    field TEXT NOT NULL,
    old_value JSONB NULL,
    new_value JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS import_lineage (
    id UUID PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES core_empresa(id),
    item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
    promoted_to TEXT NOT NULL,
    promoted_ref TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auditing: add batch/item linkage if missing
ALTER TABLE auditoria_importacion
    ADD COLUMN IF NOT EXISTS batch_id UUID NULL,
    ADD COLUMN IF NOT EXISTS item_id UUID NULL;

