-- Refuerza idempotencia del importador:
-- 1. Deduplica documentos históricos por tenant + hash
-- 2. Enlaza referencias al documento superviviente
-- 3. Crea índice único parcial por tenant + hash
-- 4. Refuerza unicidad de staging para documentos no tabulares
--
-- Idempotente: si el índice único ya existe, salta la dedup.

DO $$
BEGIN
    -- Si el índice único ya existe, solo asegurar staging y salir.
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname  = 'uq_imp_documento_tenant_hash'
    ) THEN
        RAISE NOTICE 'uq_imp_documento_tenant_hash ya existe; saltando dedup.';

        -- Asegurar staging
        UPDATE imp_staging_line
        SET sheet_name = '__document__'
        WHERE sheet_name IS NULL;

        ALTER TABLE imp_staging_line
            DROP CONSTRAINT IF EXISTS imp_staging_line_documento_id_line_number_sheet_name_key;

        ALTER TABLE imp_staging_line
            DROP CONSTRAINT IF EXISTS uq_imp_staging_line_doc_line_sheet;

        DROP INDEX IF EXISTS uq_imp_staging_line_doc_line_sheet;

        CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_staging_line_doc_line_sheet
            ON imp_staging_line (documento_id, line_number, COALESCE(sheet_name, '__document__'));

        RETURN;
    END IF;

    -- La dedup real se ejecuta en 2026-03-22_003_fix_imp_documento_dedup.
    -- Esta migración ahora es un no-op si el índice no existe todavía;
    -- la migración posterior lo creará.
    RAISE NOTICE 'Índice no existe aún; dedup se ejecutará en migración posterior.';
END $$;

-- Asegurar staging (fuera del DO para que siempre corra)
DROP INDEX IF EXISTS idx_imp_doc_hash;

UPDATE imp_staging_line
SET sheet_name = '__document__'
WHERE sheet_name IS NULL;

ALTER TABLE imp_staging_line
    DROP CONSTRAINT IF EXISTS imp_staging_line_documento_id_line_number_sheet_name_key;

ALTER TABLE imp_staging_line
    DROP CONSTRAINT IF EXISTS uq_imp_staging_line_doc_line_sheet;

DROP INDEX IF EXISTS uq_imp_staging_line_doc_line_sheet;

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_staging_line_doc_line_sheet
    ON imp_staging_line (documento_id, line_number, COALESCE(sheet_name, '__document__'));
