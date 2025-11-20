-- Migration: 2025-11-21_010_import_items_idempotency_constraint
-- Description: Ensure tenant/idempotency unique constraint is available for ON CONFLICT targets.

BEGIN;

DROP INDEX IF EXISTS uq_import_items_tenant_idem;
DROP INDEX IF EXISTS idx_import_items_tenant_idempotency;

ALTER TABLE import_items
    ADD CONSTRAINT import_items_tenant_idempotency_unique UNIQUE (tenant_id, idempotency_key);

COMMIT;
