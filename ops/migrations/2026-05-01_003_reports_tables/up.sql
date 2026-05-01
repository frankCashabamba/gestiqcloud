-- Migration: 2026-05-01_003_reports_tables
-- Create persistence tables for the Reports module:
--   * reports             — generated report records (history)
--   * scheduled_reports   — scheduled report configurations consumed by
--                            apps.backend.app.workers.reports_tasks.process_due_scheduled_reports
-- Idempotent (CREATE ... IF NOT EXISTS) so it is safe to re-apply across
-- environments where ad-hoc DDL may already have created the tables.

BEGIN;

-- ---------------------------------------------------------------------------
-- reports
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id            UUID PRIMARY KEY,
    tenant_id     UUID NOT NULL,
    name          VARCHAR(255) NOT NULL,
    report_type   VARCHAR(64) NOT NULL,
    format        VARCHAR(16) NOT NULL,
    status        VARCHAR(32) NOT NULL DEFAULT 'pending',
    file_path     TEXT,
    file_size     BIGINT,
    row_count     INTEGER,
    download_url  TEXT,
    error_message TEXT,
    generated_at  TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reports_tenant_created
    ON reports(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_reports_tenant_type
    ON reports(tenant_id, report_type);

-- RLS
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS reports_tenant_isolation ON reports;
CREATE POLICY reports_tenant_isolation ON reports
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

-- ---------------------------------------------------------------------------
-- scheduled_reports
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id                 UUID PRIMARY KEY,
    tenant_id          UUID NOT NULL,
    name               VARCHAR(255) NOT NULL,
    report_type        VARCHAR(64) NOT NULL,
    format             VARCHAR(16) NOT NULL,
    frequency          VARCHAR(32) NOT NULL,
    cron_expression    VARCHAR(128),
    recipients         TEXT NOT NULL DEFAULT '[]',
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    last_generated_at  TIMESTAMPTZ,
    next_scheduled_at  TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT data_type
    INTO col_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'scheduled_reports'
      AND column_name = 'is_active';

    IF col_type IS NULL THEN
        ALTER TABLE public.scheduled_reports
            ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    ELSIF col_type <> 'boolean' THEN
        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active DROP DEFAULT;

        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active TYPE BOOLEAN
            USING (
                CASE
                    WHEN is_active IS NULL THEN TRUE
                    WHEN lower(is_active::text) IN ('1', 't', 'true', 'yes', 'y', 'on') THEN TRUE
                    ELSE FALSE
                END
            );

        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active SET DEFAULT TRUE;
        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active SET NOT NULL;
    ELSE
        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active SET DEFAULT TRUE;
        UPDATE public.scheduled_reports
        SET is_active = TRUE
        WHERE is_active IS NULL;
        ALTER TABLE public.scheduled_reports
            ALTER COLUMN is_active SET NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_scheduled_reports_tenant
    ON scheduled_reports(tenant_id);
-- Partial index used by the scheduler worker (process_due_scheduled_reports)
-- to cheaply find rows whose next run is due.
CREATE INDEX IF NOT EXISTS ix_scheduled_reports_due
    ON scheduled_reports(next_scheduled_at)
    WHERE is_active IS TRUE;

ALTER TABLE scheduled_reports ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS scheduled_reports_tenant_isolation ON scheduled_reports;
CREATE POLICY scheduled_reports_tenant_isolation ON scheduled_reports
    USING (tenant_id::text = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true));

COMMIT;
