-- Migration: 2026-02-21_003_cost_driver_unit_types
-- Description: Cost Driver Unit Types lookup table
-- Purpose: Lookup table for unit-of-measure codes used by cost drivers
--          (hour, kWh, unit, flat per batch, etc.)
--
-- Tables created:
--   - cost_driver_unit_types: Unit type codes for cost driver allocation
--
-- Seeded values are inserted for all existing tenants.

BEGIN;

-- ============================================================================
-- Cost Driver Unit Types
-- ============================================================================
-- Ensure UUID generator is available (needed for gen_random_uuid())
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS cost_driver_unit_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_cost_driver_unit_per_tenant UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_cost_driver_unit_types_tenant ON cost_driver_unit_types(tenant_id);
CREATE INDEX IF NOT EXISTS ix_cost_driver_unit_types_code ON cost_driver_unit_types(code);
CREATE INDEX IF NOT EXISTS ix_cost_driver_unit_types_active ON cost_driver_unit_types(is_active);

-- ============================================================================
-- Get all tenant IDs (for seeding across all tenants)
-- ============================================================================
-- Allow reruns: drop leftover temp table from previous attempt
DROP TABLE IF EXISTS tenant_list;

CREATE TEMP TABLE tenant_list AS
SELECT DISTINCT id
FROM tenants
WHERE COALESCE(active, TRUE) = TRUE
LIMIT 1;

-- Fallback: if no active tenant exists, use any tenant
INSERT INTO tenant_list (id)
SELECT t.id
FROM tenants t
WHERE NOT EXISTS (SELECT 1 FROM tenant_list)
LIMIT 1;

-- ============================================================================
-- Seed Cost Driver Unit Types
-- ============================================================================
INSERT INTO cost_driver_unit_types (
    tenant_id, code, name_en, name_es, sort_order
)
SELECT
    t.id, 'hour', 'Hour', 'Hora', 1
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM cost_driver_unit_types WHERE tenant_id = t.id AND code = 'hour')

UNION ALL

SELECT
    t.id, 'kwh', 'kWh', 'kWh', 2
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM cost_driver_unit_types WHERE tenant_id = t.id AND code = 'kwh')

UNION ALL

SELECT
    t.id, 'unit', 'Unit', 'Unidad', 3
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM cost_driver_unit_types WHERE tenant_id = t.id AND code = 'unit')

UNION ALL

SELECT
    t.id, 'flat', 'Flat per batch', 'Fijo por lote', 4
FROM tenant_list t
WHERE NOT EXISTS (SELECT 1 FROM cost_driver_unit_types WHERE tenant_id = t.id AND code = 'flat');

COMMIT;
