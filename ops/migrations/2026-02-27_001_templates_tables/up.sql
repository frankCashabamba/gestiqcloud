-- Minimal tables for UI template packages (used by /api/v1/tenant/templates/ui-config)
-- Compatible con PostgreSQL; en SQLite los tipos JSONB/UUID se aceptan como alias.

-- UUID helper (PostgreSQL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        CREATE EXTENSION pgcrypto;
    END IF;
EXCEPTION
    WHEN undefined_table THEN
        -- Running on SQLite or engine without extensions; ignore
        NULL;
END$$;

CREATE TABLE IF NOT EXISTS template_packages (
    template_key TEXT NOT NULL,
    version      INTEGER NOT NULL,
    config       JSONB NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (template_key, version)
);

CREATE TABLE IF NOT EXISTS tenant_templates (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL,
    template_key TEXT NOT NULL,
    version      INTEGER NOT NULL,
    active       BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, template_key, version)
);

CREATE INDEX IF NOT EXISTS ix_tenant_templates_tenant ON tenant_templates (tenant_id, active);
