-- Convierte el índice único de expresión uq_imp_staging_line_doc_line_sheet
-- en un UNIQUE CONSTRAINT nombrado sobre columnas escalares.
--
-- Contexto:
--   La migración 2026-03-20 creó un índice único con COALESCE:
--       (documento_id, line_number, COALESCE(sheet_name, '__document__'))
--   Eso impedía usar ON CONFLICT (columna, ...) en los INSERT porque PostgreSQL
--   no permite referencias a expresiones de función en la conflict_target.
--
--   Desde la migración 2026-03-20 sheet_name nunca es NULL:
--   - documentos no tabulares usan el centinela '__document__'
--   - documentos tabulares usan el nombre de hoja real
--   Por tanto la expresión COALESCE ya no añade valor y podemos reemplazarla
--   por un UNIQUE CONSTRAINT normal, que sí acepta ON CONFLICT DO NOTHING
--   sin necesidad de nombrar el constraint explícitamente.
--
-- Idempotente: envuelto en DO $$ ... $$ con guardas IF EXISTS.

DO $$
BEGIN
    -- Eliminar el índice de expresión antiguo si todavía existe
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname  = 'uq_imp_staging_line_doc_line_sheet'
    ) THEN
        DROP INDEX uq_imp_staging_line_doc_line_sheet;
    END IF;

    -- Crear el UNIQUE CONSTRAINT nombrado solo si no existe ya
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'imp_staging_line'::regclass
          AND conname   = 'uq_imp_staging_line_doc_line_sheet'
          AND contype   = 'u'
    ) THEN
        -- Seguridad: garantizar que no haya NULLs residuales antes de crear el constraint
        UPDATE imp_staging_line
        SET sheet_name = '__document__'
        WHERE sheet_name IS NULL;

        ALTER TABLE imp_staging_line
            ADD CONSTRAINT uq_imp_staging_line_doc_line_sheet
            UNIQUE (documento_id, line_number, sheet_name);
    END IF;
END $$;
