-- Ensure UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- import_batches
CREATE TABLE IF NOT EXISTS import_batches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  empresa_id INTEGER NOT NULL,
  source_type TEXT NOT NULL,
  origin TEXT NOT NULL,
  file_key TEXT NULL,
  mapping_id UUID NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  created_by TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- import_items
CREATE TABLE IF NOT EXISTS import_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  batch_id UUID NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
  idx INTEGER NOT NULL,
  status TEXT NOT NULL,
  raw JSONB,
  normalized JSONB,
  errors JSONB,
  idempotency_key TEXT,
  dedupe_hash TEXT,
  promoted_to TEXT,
  promoted_id UUID,
  promoted_at TIMESTAMPTZ
);

-- import_mappings (plantillas)
CREATE TABLE IF NOT EXISTS import_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  empresa_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  mappings JSONB,
  transforms JSONB,
  defaults JSONB,
  dedupe_keys JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- import_lineage (trazabilidad)
CREATE TABLE IF NOT EXISTS import_lineage (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  empresa_id INTEGER NOT NULL,
  item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
  promoted_to TEXT NOT NULL,
  promoted_ref TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- import_item_corrections (historial de correcciones)
CREATE TABLE IF NOT EXISTS import_item_corrections (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  empresa_id INTEGER NOT NULL,
  item_id UUID NOT NULL REFERENCES import_items(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  field TEXT NOT NULL,
  old_value JSONB,
  new_value JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Helpful indexes
-- batches by empresa and recency
CREATE INDEX IF NOT EXISTS ix_import_batches_empresa_created ON import_batches (empresa_id, created_at DESC);

-- items natural order within batch
CREATE INDEX IF NOT EXISTS ix_import_items_batch_idx ON import_items (batch_id, idx);

-- idempotency per batch (skip duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS ux_import_items_batch_id_idem
ON import_items (batch_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

-- fast check of dedupe promoted
CREATE INDEX IF NOT EXISTS ix_import_items_promoted_hash
ON import_items (dedupe_hash) WHERE status = 'PROMOTED';

-- lineage by item
CREATE INDEX IF NOT EXISTS ix_import_lineage_item ON import_lineage (item_id);

