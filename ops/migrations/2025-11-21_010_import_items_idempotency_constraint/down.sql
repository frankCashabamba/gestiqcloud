-- Migration: 2025-11-21_010_import_items_idempotency_constraint (rollback)

BEGIN;

ALTER TABLE import_items
    DROP CONSTRAINT IF EXISTS import_items_tenant_idempotency_unique;

CREATE UNIQUE INDEX IF NOT EXISTS uq_import_items_tenant_idem
    ON import_items(batch_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_import_items_tenant_idempotency
    ON import_items(tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMIT;
