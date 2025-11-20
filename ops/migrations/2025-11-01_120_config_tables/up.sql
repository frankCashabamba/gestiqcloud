-- =====================================================
-- CONFIG TABLES: Doc Series, Base Roles
-- Migration: 2025-11-01_120_config_tables
-- =====================================================

BEGIN;

-- =====================================================
-- BASE_ROLES: Global Role Definitions
-- =====================================================
CREATE TABLE IF NOT EXISTS base_roles (
    id UUID DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (id)
);

-- =====================================================
-- DOC_SERIES: Document Numbering Series
-- =====================================================
CREATE TABLE IF NOT EXISTS doc_series (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    register_id UUID,
    doc_type VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    current_no INTEGER NOT NULL DEFAULT 0,
    reset_policy VARCHAR(20) NOT NULL DEFAULT 'yearly',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (register_id) REFERENCES pos_registers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_doc_series_id ON doc_series(id);
CREATE INDEX IF NOT EXISTS idx_doc_series_tenant_id ON doc_series(tenant_id);
CREATE INDEX IF NOT EXISTS idx_doc_series_register_id ON doc_series(register_id);

COMMIT;
