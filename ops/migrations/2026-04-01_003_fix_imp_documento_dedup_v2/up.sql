-- Reintento de 2026-03-22_003_fix_imp_documento_dedup que falló porque
-- la deduplicación con NOT IN/DISTINCT ON no eliminó todos los duplicados.
-- Este script usa ROW_NUMBER() que es más robusto para tablas grandes.
-- Es idempotente: si el índice ya existe, sale inmediatamente.

DO $$
DECLARE
    v_nulled  integer;
    v_dup_cnt integer;
BEGIN
    -- Si el índice ya existe, nada que hacer.
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname  = 'uq_imp_documento_tenant_hash'
    ) THEN
        RAISE NOTICE 'uq_imp_documento_tenant_hash ya existe; nada que hacer.';
        RETURN;
    END IF;

    -- 0. Normalizar hashes vacíos o solo-espacios a NULL
    UPDATE imp_documento
    SET hash_sha256 = NULL
    WHERE hash_sha256 IS NOT NULL AND TRIM(hash_sha256) = '';

    -- 1. Anular hash en filas duplicadas usando ROW_NUMBER().
    --    Se conserva la fila con mejor estado y más reciente por (tenant_id, hash_sha256).
    WITH ranked AS (
        SELECT
            id,
            ROW_NUMBER() OVER (
                PARTITION BY tenant_id, hash_sha256
                ORDER BY
                    CASE estado
                        WHEN 'CONFIRMED'  THEN 0
                        WHEN 'REVIEW'     THEN 1
                        WHEN 'PENDING'    THEN 2
                        WHEN 'PROCESSING' THEN 3
                        WHEN 'FAILED'     THEN 4
                        ELSE 5
                    END,
                    created_at DESC,
                    id
            ) AS rn
        FROM imp_documento
        WHERE hash_sha256 IS NOT NULL
    )
    UPDATE imp_documento d
    SET hash_sha256 = NULL
    FROM ranked r
    WHERE d.id = r.id
      AND r.rn > 1;

    GET DIAGNOSTICS v_nulled = ROW_COUNT;
    RAISE NOTICE 'Filas anuladas (duplicados): %', v_nulled;

    -- 2. Verificación: no deben quedar duplicados
    SELECT COUNT(*)
    INTO v_dup_cnt
    FROM (
        SELECT 1
        FROM imp_documento
        WHERE hash_sha256 IS NOT NULL
        GROUP BY tenant_id, hash_sha256
        HAVING count(*) > 1
    ) sub;

    IF v_dup_cnt > 0 THEN
        RAISE EXCEPTION 'Aún quedan % grupo(s) duplicados tras anular hashes. Abortar.', v_dup_cnt;
    END IF;

    -- 3. Crear el índice único parcial
    CREATE UNIQUE INDEX uq_imp_documento_tenant_hash
        ON imp_documento (tenant_id, hash_sha256)
        WHERE hash_sha256 IS NOT NULL;

    RAISE NOTICE 'uq_imp_documento_tenant_hash creado exitosamente. Filas anuladas: %', v_nulled;
END $$;
