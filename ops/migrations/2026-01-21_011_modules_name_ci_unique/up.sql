-- Deduplicate modules differing only by case and enforce case-insensitive unique names.
CREATE TEMP TABLE IF NOT EXISTS tmp_module_dedup (
    keep_id UUID,
    module_id UUID
) ON COMMIT DROP;

WITH normalized AS (
    SELECT
        id,
        lower(name) AS normalized_name,
        row_number() OVER (PARTITION BY lower(name) ORDER BY id) AS rn
    FROM modules
),
duplicates AS (
    SELECT normalized_name, id AS module_id
    FROM normalized
    WHERE rn > 1
),
keepers AS (
    SELECT normalized_name, id AS keep_id
    FROM normalized
    WHERE rn = 1
)
INSERT INTO tmp_module_dedup (keep_id, module_id)
SELECT k.keep_id, d.module_id
FROM duplicates d
JOIN keepers k USING (normalized_name);

UPDATE company_modules
SET module_id = tmp.keep_id
FROM tmp_module_dedup AS tmp
WHERE company_modules.module_id = tmp.module_id;

UPDATE assigned_modules
SET module_id = tmp.keep_id
FROM tmp_module_dedup AS tmp
WHERE assigned_modules.module_id = tmp.module_id;

DELETE FROM modules
WHERE id IN (SELECT module_id FROM tmp_module_dedup);

DROP TABLE IF EXISTS tmp_module_dedup;

CREATE UNIQUE INDEX IF NOT EXISTS uq_modules_name_lower ON modules (lower(name));
