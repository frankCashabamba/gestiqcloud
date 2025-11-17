-- ============================================================================
-- Migration: 2025-11-18_350_import_mappings_corrections
-- Description: Additional import mappings and item corrections tables
-- ============================================================================

BEGIN;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Table: import_mappings (Alterations to existing table)
-- ============================================================================

-- Add missing columns to import_mappings if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'import_mappings' AND column_name = 'is_active') THEN
        ALTER TABLE import_mappings ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'import_mappings' AND column_name = 'is_template') THEN
        ALTER TABLE import_mappings ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'import_mappings' AND column_name = 'description') THEN
        ALTER TABLE import_mappings ADD COLUMN description TEXT;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'import_mappings' AND column_name = 'mapping_config') THEN
        ALTER TABLE import_mappings ADD COLUMN mapping_config JSONB;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'import_mappings' AND column_name = 'updated_at') THEN
        ALTER TABLE import_mappings ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    END IF;
END;
$$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_import_mappings_tenant ON import_mappings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_import_mappings_name ON import_mappings(name);
CREATE INDEX IF NOT EXISTS idx_import_mappings_is_active ON import_mappings(is_active) WHERE is_active = TRUE;

-- Add unique constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'import_mappings_tenant_name_unique'
        AND table_name = 'import_mappings'
    ) THEN
        ALTER TABLE import_mappings
        ADD CONSTRAINT import_mappings_tenant_name_unique UNIQUE (tenant_id, name);
    END IF;
END;
$$;

COMMENT ON TABLE import_mappings IS 'Field mappings for import processing';
COMMENT ON COLUMN import_mappings.mapping_config IS 'Mapping rules in JSON format';

-- Ensure RLS is enabled
ALTER TABLE import_mappings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_import_mappings ON import_mappings;
CREATE POLICY tenant_isolation_import_mappings ON import_mappings
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Note: import_item_corrections table is already created in migration 2025-11-02_300_import_batches_system
-- This section is skipped to avoid conflicts

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'import_mappings_updated_at'
    ) THEN
        CREATE TRIGGER import_mappings_updated_at
            BEFORE UPDATE ON import_mappings
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
