DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'import_ocr_jobs'
    ) THEN
        EXECUTE $ddl$
            CREATE TABLE import_ocr_jobs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                empresa_id INTEGER NOT NULL REFERENCES core_empresa(id),
                filename TEXT NOT NULL,
                content_type TEXT,
                payload BYTEA NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result JSONB,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        $ddl$;
    END IF;

    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_status_created ON import_ocr_jobs (status, created_at)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_import_ocr_jobs_empresa_created ON import_ocr_jobs (empresa_id, created_at)';

    UPDATE import_ocr_jobs
    SET status = 'pending',
        error = NULL,
        updated_at = NOW()
    WHERE status = 'running';
END
$$;
