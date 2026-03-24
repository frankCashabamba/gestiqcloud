-- Retoma la deduplicación de 2026-03-20_000_importador_hash_idempotency que falló
-- en producción porque quedaron duplicados no capturados.
--
-- Estrategia robusta:
--   a) Limpia empty-string hashes (los trata como NULL).
--   b) Dedup con DELETE ... USING y temp tables.
--   c) Segundo pase directo para capturar cualquier caso residual.
--   d) Crea el índice único.
-- Es idempotente: si el índice ya existe, no hace nada.

DO $$
BEGIN
    -- Si el índice ya existe, la migración anterior terminó bien; salir.
    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname  = 'uq_imp_documento_tenant_hash'
    ) THEN
        RAISE NOTICE 'uq_imp_documento_tenant_hash ya existe; nada que hacer.';
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- 0. Normalizar hashes vacíos a NULL (no participan en la unicidad)
    -- ----------------------------------------------------------------
    UPDATE imp_documento
    SET hash_sha256 = NULL
    WHERE hash_sha256 IS NOT NULL AND TRIM(hash_sha256) = '';

    -- ----------------------------------------------------------------
    -- 1. Tabla temporal de supervivientes: un id por (tenant_id, hash_sha256)
    --    Criterio: mejor estado → created_at más reciente → id menor (desempate)
    -- ----------------------------------------------------------------
    DROP TABLE IF EXISTS _fix_survivors;
    CREATE TEMP TABLE _fix_survivors AS
    SELECT DISTINCT ON (tenant_id, hash_sha256)
        id            AS survivor_id,
        tenant_id,
        hash_sha256
    FROM imp_documento
    WHERE hash_sha256 IS NOT NULL
    ORDER BY
        tenant_id,
        hash_sha256,
        CASE estado
            WHEN 'CONFIRMED'  THEN 0
            WHEN 'REVIEW'     THEN 1
            WHEN 'PENDING'    THEN 2
            WHEN 'PROCESSING' THEN 3
            WHEN 'FAILED'     THEN 4
            ELSE 5
        END,
        created_at DESC,
        id;

    -- ----------------------------------------------------------------
    -- 2. Tabla temporal de duplicados a eliminar
    -- ----------------------------------------------------------------
    DROP TABLE IF EXISTS _fix_dupes;
    CREATE TEMP TABLE _fix_dupes AS
    SELECT d.id AS dup_id, s.survivor_id
    FROM imp_documento d
    JOIN _fix_survivors s
        ON  s.tenant_id   = d.tenant_id
        AND s.hash_sha256 = d.hash_sha256
    WHERE d.id <> s.survivor_id;

    IF NOT EXISTS (SELECT 1 FROM _fix_dupes) THEN
        RAISE NOTICE 'No se encontraron duplicados; solo crea el índice.';
    ELSE
        RAISE NOTICE 'Deduplicando % filas...', (SELECT count(*) FROM _fix_dupes);

        -- ----------------------------------------------------------------
        -- 3. Redirigir hijos al superviviente antes de eliminar el duplicado
        -- ----------------------------------------------------------------
        UPDATE imp_log_cambios l
        SET documento_id = fd.survivor_id
        FROM _fix_dupes fd
        WHERE l.documento_id = fd.dup_id;

        UPDATE imp_batch_item bi
        SET documento_id = fd.survivor_id
        FROM _fix_dupes fd
        WHERE bi.documento_id = fd.dup_id;

        UPDATE imp_staging_line sl
        SET documento_id = fd.survivor_id
        FROM _fix_dupes fd
        WHERE sl.documento_id = fd.dup_id;

        UPDATE imp_iteration it
        SET documento_id = fd.survivor_id
        FROM _fix_dupes fd
        WHERE it.documento_id = fd.dup_id;

        UPDATE imp_review_session rs
        SET documento_id = fd.survivor_id
        FROM _fix_dupes fd
        WHERE rs.documento_id = fd.dup_id;

        IF to_regclass('public.daily_production_logs') IS NOT NULL THEN
            UPDATE daily_production_logs dl
            SET source_document_id = fd.survivor_id
            FROM _fix_dupes fd
            WHERE dl.source_document_id = fd.dup_id;
        END IF;

        IF to_regclass('public.imp_documento_successor') IS NOT NULL THEN
            DROP TABLE IF EXISTS _fix_succ_norm;
            CREATE TEMP TABLE _fix_succ_norm AS
            SELECT DISTINCT
                COALESCE(fp.survivor_id, s.predecessor_id) AS predecessor_id,
                COALESCE(fs.survivor_id, s.successor_id)   AS successor_id,
                MIN(s.reason)      AS reason,
                MIN(s.created_at)  AS created_at
            FROM imp_documento_successor s
            LEFT JOIN _fix_dupes fp ON fp.dup_id = s.predecessor_id
            LEFT JOIN _fix_dupes fs ON fs.dup_id = s.successor_id
            GROUP BY 1, 2;

            DELETE FROM imp_documento_successor;

            INSERT INTO imp_documento_successor (id, predecessor_id, successor_id, reason, created_at)
            SELECT gen_random_uuid(), predecessor_id, successor_id, reason, created_at
            FROM _fix_succ_norm
            WHERE predecessor_id <> successor_id;
        END IF;

        -- ----------------------------------------------------------------
        -- 4. Eliminar duplicados usando JOIN explícito
        -- ----------------------------------------------------------------
        DELETE FROM imp_documento d
        USING _fix_dupes fd
        WHERE d.id = fd.dup_id;
    END IF;

    -- ----------------------------------------------------------------
    -- 4b. Segundo pase: eliminar cualquier duplicado residual directamente.
    --     Las FK son CASCADE / SET NULL, así que es seguro.
    -- ----------------------------------------------------------------
    DELETE FROM imp_documento
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

    -- Verificación final
    IF EXISTS (
        SELECT tenant_id, hash_sha256
        FROM imp_documento
        WHERE hash_sha256 IS NOT NULL
        GROUP BY tenant_id, hash_sha256
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Aún quedan duplicados en imp_documento tras la limpieza. Abortar.';
    END IF;

    -- ----------------------------------------------------------------
    -- 5. Crear el índice único
    -- ----------------------------------------------------------------
    CREATE UNIQUE INDEX uq_imp_documento_tenant_hash
        ON imp_documento (tenant_id, hash_sha256)
        WHERE hash_sha256 IS NOT NULL;

    RAISE NOTICE 'uq_imp_documento_tenant_hash creado exitosamente.';
END $$;
