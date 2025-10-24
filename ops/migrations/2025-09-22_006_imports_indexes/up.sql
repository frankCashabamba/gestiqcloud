-- Ensure critical indexes for imports module (idempotent)

-- items natural order within batch
CREATE INDEX IF NOT EXISTS ix_import_items_batch_idx ON import_items (batch_id, idx);

-- batches by empresa and recency
CREATE INDEX IF NOT EXISTS ix_import_batches_empresa_created ON import_batches (empresa_id, created_at DESC);

-- idempotency per batch (skip duplicates)
CREATE UNIQUE INDEX IF NOT EXISTS ux_import_items_batch_id_idem
ON import_items (batch_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

-- fast check of dedupe promoted
CREATE INDEX IF NOT EXISTS ix_import_items_promoted_hash
ON import_items (dedupe_hash) WHERE status = 'PROMOTED';

