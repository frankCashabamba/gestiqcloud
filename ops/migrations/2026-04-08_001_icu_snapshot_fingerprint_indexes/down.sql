BEGIN;

DROP INDEX IF EXISTS idx_icu_snapshot_tenant_fingerprint_kind_created;
DROP INDEX IF EXISTS idx_icu_snapshot_tenant_fingerprint_signature_created;
DROP INDEX IF EXISTS idx_icu_snapshot_tenant_fingerprint_hash_created;

COMMIT;
