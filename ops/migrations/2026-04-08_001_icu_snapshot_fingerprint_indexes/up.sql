BEGIN;

-- Backfill fingerprint_kind where the embedded fingerprint already exposes a kind.
UPDATE icu_recipe_snapshot
SET content_json = jsonb_set(
    content_json,
    '{fingerprint_kind}',
    to_jsonb(lower(content_json -> 'fingerprint' ->> 'kind')),
    true
)
WHERE content_json ? 'fingerprint'
  AND COALESCE(content_json ->> 'fingerprint_kind', '') = ''
  AND COALESCE(content_json -> 'fingerprint' ->> 'kind', '') <> '';

-- Exact-match lookup by tenant + fingerprint_hash.
CREATE INDEX IF NOT EXISTS idx_icu_snapshot_tenant_fingerprint_hash_created
    ON icu_recipe_snapshot (
        tenant_id,
        jsonb_extract_path_text(content_json, 'fingerprint_hash'),
        created_at DESC
    )
    WHERE content_json ? 'fingerprint_hash';

-- Exact-match lookup by tenant + fingerprint_signature.
CREATE INDEX IF NOT EXISTS idx_icu_snapshot_tenant_fingerprint_signature_created
    ON icu_recipe_snapshot (
        tenant_id,
        jsonb_extract_path_text(content_json, 'fingerprint_signature'),
        created_at DESC
    )
    WHERE content_json ? 'fingerprint_signature';

-- Candidate narrowing for Excel fuzzy reuse and future snapshot scans by kind.
CREATE INDEX IF NOT EXISTS idx_icu_snapshot_tenant_fingerprint_kind_created
    ON icu_recipe_snapshot (
        tenant_id,
        jsonb_extract_path_text(content_json, 'fingerprint_kind'),
        created_at DESC
    )
    WHERE content_json ? 'fingerprint_kind';

COMMIT;
