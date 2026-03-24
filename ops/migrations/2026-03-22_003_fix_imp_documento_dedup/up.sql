-- Retoma la deduplicación de 2026-03-20_000_importador_hash_idempotency que falló
-- en producción porque quedaron duplicados no capturados.
--
-- Estrategia: en vez de DELETE (que puede fallar por constraints en tablas hijas),
-- simplemente anula el hash de las filas duplicadas. El índice parcial
-- (WHERE hash_sha256 IS NOT NULL) las excluye automáticamente.
-- Es idempotente: si el índice ya existe, no hace nada.

DO $$
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

    -- 0. Normalizar hashes vacíos a NULL
    UPDATE imp_documento
    SET hash_sha256 = NULL
    WHERE hash_sha256 IS NOT NULL AND TRIM(hash_sha256) = '';

    -- 1. Anular hash en filas duplicadas, conservando solo el mejor registro
    --    por (tenant_id, hash_sha256).
    UPDATE imp_documento
    SET hash_sha256 = NULL
    WHERE hash_sha256 IS NOT NULL
      AND id NOT IN (
          SELECT DISTINCT ON (tenant_id, hash_sha256) id
          FROM imp_documento
          WHERE hash_sha256 IS NOT NULL
          ORDER BY tenant_id, hash_sha256,
              CASE estado
                  WHEN 'CONFIRMED'  THEN 0
                  WHEN 'REVIEW'     THEN 1
                  WHEN 'PENDING'    THEN 2
                  WHEN 'PROCESSING' THEN 3
                  WHEN 'FAILED'     THEN 4
                  ELSE 5
              END,
              created_at DESC, id
      );

    -- Verificación
    IF EXISTS (
        SELECT tenant_id, hash_sha256
        FROM imp_documento
        WHERE hash_sha256 IS NOT NULL
        GROUP BY tenant_id, hash_sha256
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Aún quedan duplicados tras anular hashes. Abortar.';
    END IF;

    -- 2. Crear el índice único
    CREATE UNIQUE INDEX uq_imp_documento_tenant_hash
        ON imp_documento (tenant_id, hash_sha256)
        WHERE hash_sha256 IS NOT NULL;

    RAISE NOTICE 'uq_imp_documento_tenant_hash creado exitosamente.';
END $$;
