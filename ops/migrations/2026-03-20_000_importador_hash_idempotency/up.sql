-- Refuerza idempotencia del importador:
-- 1. Deduplica documentos históricos por tenant + hash
-- 2. Enlaza referencias al documento superviviente
-- 3. Crea índice único parcial por tenant + hash
-- 4. Refuerza unicidad de staging para documentos no tabulares

BEGIN;

DROP INDEX IF EXISTS idx_imp_doc_hash;

CREATE TEMP TABLE _imp_documento_dupes AS
WITH ranked AS (
    SELECT
        id,
        tenant_id,
        hash_sha256,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, hash_sha256
            ORDER BY
                CASE estado
                    WHEN 'CONFIRMED' THEN 0
                    WHEN 'REVIEW' THEN 1
                    WHEN 'PENDING' THEN 2
                    WHEN 'PROCESSING' THEN 3
                    WHEN 'FAILED' THEN 4
                    ELSE 5
                END,
                created_at DESC,
                id
        ) AS rn,
        FIRST_VALUE(id) OVER (
            PARTITION BY tenant_id, hash_sha256
            ORDER BY
                CASE estado
                    WHEN 'CONFIRMED' THEN 0
                    WHEN 'REVIEW' THEN 1
                    WHEN 'PENDING' THEN 2
                    WHEN 'PROCESSING' THEN 3
                    WHEN 'FAILED' THEN 4
                    ELSE 5
                END,
                created_at DESC,
                id
        ) AS survivor_id
    FROM imp_documento
    WHERE hash_sha256 IS NOT NULL
)
SELECT id AS duplicate_id, survivor_id
FROM ranked
WHERE rn > 1;

UPDATE imp_log_cambios l
SET documento_id = d.survivor_id
FROM _imp_documento_dupes d
WHERE l.documento_id = d.duplicate_id;

UPDATE imp_batch_item bi
SET documento_id = d.survivor_id
FROM _imp_documento_dupes d
WHERE bi.documento_id = d.duplicate_id;

UPDATE imp_staging_line sl
SET documento_id = d.survivor_id
FROM _imp_documento_dupes d
WHERE sl.documento_id = d.duplicate_id;

UPDATE imp_iteration it
SET documento_id = d.survivor_id
FROM _imp_documento_dupes d
WHERE it.documento_id = d.duplicate_id;

UPDATE imp_review_session rs
SET documento_id = d.survivor_id
FROM _imp_documento_dupes d
WHERE rs.documento_id = d.duplicate_id;

DO $$
BEGIN
    IF to_regclass('public.daily_production_logs') IS NOT NULL THEN
        UPDATE daily_production_logs dl
        SET source_document_id = d.survivor_id
        FROM _imp_documento_dupes d
        WHERE dl.source_document_id = d.duplicate_id;
    END IF;
END $$;

DO $$
BEGIN
    IF to_regclass('public.imp_documento_successor') IS NOT NULL THEN
        CREATE TEMP TABLE _imp_documento_successor_norm AS
        SELECT DISTINCT
            COALESCE(dp.survivor_id, s.predecessor_id) AS predecessor_id,
            COALESCE(ds.survivor_id, s.successor_id) AS successor_id,
            MIN(s.reason) AS reason,
            MIN(s.created_at) AS created_at
        FROM imp_documento_successor s
        LEFT JOIN _imp_documento_dupes dp ON dp.duplicate_id = s.predecessor_id
        LEFT JOIN _imp_documento_dupes ds ON ds.duplicate_id = s.successor_id
        GROUP BY 1, 2;

        DELETE FROM imp_documento_successor;

        INSERT INTO imp_documento_successor (id, predecessor_id, successor_id, reason, created_at)
        SELECT gen_random_uuid(), predecessor_id, successor_id, reason, created_at
        FROM _imp_documento_successor_norm
        WHERE predecessor_id <> successor_id;
    END IF;
END $$;

DELETE FROM imp_documento d
USING _imp_documento_dupes dup
WHERE d.id = dup.duplicate_id;

-- Second pass: remove any remaining duplicates not captured by the initial temp table
-- (handles concurrent inserts or edge cases; relies on CASCADE/SET NULL FK policies)
DELETE FROM imp_documento
WHERE hash_sha256 IS NOT NULL
  AND id NOT IN (
    SELECT DISTINCT ON (tenant_id, hash_sha256) id
    FROM imp_documento
    WHERE hash_sha256 IS NOT NULL
    ORDER BY
        tenant_id,
        hash_sha256,
        CASE estado
            WHEN 'CONFIRMED' THEN 0
            WHEN 'REVIEW' THEN 1
            WHEN 'PENDING' THEN 2
            WHEN 'PROCESSING' THEN 3
            WHEN 'FAILED' THEN 4
            ELSE 5
        END,
        created_at DESC,
        id
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_documento_tenant_hash
    ON imp_documento (tenant_id, hash_sha256)
    WHERE hash_sha256 IS NOT NULL;

UPDATE imp_staging_line
SET sheet_name = '__document__'
WHERE sheet_name IS NULL;

ALTER TABLE imp_staging_line
    DROP CONSTRAINT IF EXISTS imp_staging_line_documento_id_line_number_sheet_name_key;

DROP INDEX IF EXISTS uq_imp_staging_line_doc_line_sheet;

CREATE UNIQUE INDEX uq_imp_staging_line_doc_line_sheet
    ON imp_staging_line (documento_id, line_number, COALESCE(sheet_name, '__document__'));

COMMIT;
