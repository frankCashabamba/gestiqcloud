-- Migration: 2025-11-02_400_import_column_mappings
-- Description: Create import_column_mappings table for saved column mapping templates

CREATE TABLE IF NOT EXISTS import_column_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    file_pattern TEXT,
    mapping JSONB NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    use_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT fk_column_mappings_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_column_mappings_tenant ON import_column_mappings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_column_mappings_active ON import_column_mappings(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_column_mappings_last_used ON import_column_mappings(last_used_at DESC NULLS LAST);

-- RLS Policy
ALTER TABLE import_column_mappings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_column_mappings ON import_column_mappings;
CREATE POLICY tenant_isolation_column_mappings ON import_column_mappings
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

COMMENT ON TABLE import_column_mappings IS 'Saved column mapping templates for Excel/CSV imports';
COMMENT ON COLUMN import_column_mappings.mapping IS 'JSON mapping of source columns to target fields';
COMMENT ON COLUMN import_column_mappings.file_pattern IS 'Optional regex pattern to auto-match files';
