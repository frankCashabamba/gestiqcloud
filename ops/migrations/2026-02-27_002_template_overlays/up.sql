-- Support table for UI template overrides (/api/v1/tenant/templates/ui-config)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        CREATE EXTENSION pgcrypto;
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        NULL;
END$$;

CREATE TABLE IF NOT EXISTS template_overlays (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL,
    config     JSONB NOT NULL,
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_template_overlays_tenant ON template_overlays (tenant_id, active);
