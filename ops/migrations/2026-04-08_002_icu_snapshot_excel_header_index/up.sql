BEGIN;

-- Backfill flattened Excel headers for fuzzy reuse pre-filtering.
UPDATE icu_recipe_snapshot AS snap
SET content_json = jsonb_set(
    snap.content_json,
    '{fingerprint_headers_flat}',
    COALESCE(
        (
            SELECT to_jsonb(array_agg(header ORDER BY header))
            FROM (
                SELECT DISTINCT lower(btrim(elem.header)) AS header
                FROM jsonb_each(COALESCE(snap.content_json -> 'fingerprint' -> 'sheets', '{}'::jsonb)) AS sheet(key, value)
                CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(sheet.value -> 'headers', '[]'::jsonb)) AS elem(header)
                WHERE NULLIF(btrim(elem.header), '') IS NOT NULL
            ) AS normalized_headers
        ),
        '[]'::jsonb
    ),
    true
)
WHERE COALESCE(snap.content_json ->> 'fingerprint_kind', '') = 'excel'
  AND (
      NOT (snap.content_json ? 'fingerprint_headers_flat')
      OR jsonb_typeof(snap.content_json -> 'fingerprint_headers_flat') <> 'array'
  );

CREATE INDEX IF NOT EXISTS idx_icu_snapshot_excel_headers_flat_gin
    ON icu_recipe_snapshot
    USING GIN ((content_json -> 'fingerprint_headers_flat'))
    WHERE content_json ? 'fingerprint_headers_flat'
      AND jsonb_extract_path_text(content_json, 'fingerprint_kind') = 'excel';

COMMIT;
