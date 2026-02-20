-- Migration: 2026-02-18_000_hr_lookup_tables
-- Description: HR Module — Lookup tables for employee-related enumerations
-- Purpose: Replace hardcoded enums with database-driven lookup tables for
--          multi-tenant configurability
--
-- Tables created:
--   - employee_statuses: Employment status codes (ACTIVE, INACTIVE, ON_LEAVE, TERMINATED, etc)
--   - contract_types: Contract type codes (PERMANENT, TEMPORARY, PART_TIME, APPRENTICE, CONTRACTOR)
--   - deduction_types: Deduction/bonus type codes (INCOME_TAX, SOCIAL_SECURITY, HEALTH_INSURANCE, etc)
--   - gender_types: Gender/social classification codes (MALE, FEMALE, OTHER, PREFER_NOT_TO_SAY, etc)
--
-- All tables include tenant_id for multi-tenancy support and i18n support.

BEGIN;

-- ============================================================================
-- Employee Status Types
-- ============================================================================
-- Employment status codes for use in the employees table
CREATE TABLE IF NOT EXISTS employee_statuses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    description_en TEXT,
    description_es TEXT,
    description_pt TEXT,
    color_code VARCHAR(7),  -- Hex color for UI (e.g., #22c55e for green)
    icon_code VARCHAR(50),  -- Icon name for UI (e.g., check-circle)
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,
    updated_by UUID,

    CONSTRAINT uq_employee_status_per_tenant UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_employee_statuses_tenant ON employee_statuses(tenant_id);
CREATE INDEX IF NOT EXISTS ix_employee_statuses_code ON employee_statuses(code);
CREATE INDEX IF NOT EXISTS ix_employee_statuses_active ON employee_statuses(is_active);

-- ============================================================================
-- Contract Types
-- ============================================================================
-- Employment contract type codes
CREATE TABLE IF NOT EXISTS contract_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    description_en TEXT,
    description_es TEXT,
    description_pt TEXT,

    -- Contract characteristics
    is_permanent BOOLEAN DEFAULT TRUE,  -- Permanent (indefinite) vs temporary
    full_time BOOLEAN DEFAULT TRUE,     -- Full-time vs part-time
    requires_probation BOOLEAN DEFAULT FALSE,
    probation_months INTEGER,
    notice_period_days INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,
    updated_by UUID,

    CONSTRAINT uq_contract_type_per_tenant UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_contract_types_tenant ON contract_types(tenant_id);
CREATE INDEX IF NOT EXISTS ix_contract_types_code ON contract_types(code);
CREATE INDEX IF NOT EXISTS ix_contract_types_active ON contract_types(is_active);

-- ============================================================================
-- Deduction Types
-- ============================================================================
-- Employee deduction/bonus type codes (INCOME_TAX, SOCIAL_SECURITY, etc)
CREATE TABLE IF NOT EXISTS deduction_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    description_en TEXT,
    description_es TEXT,
    description_pt TEXT,

    -- Deduction characteristics
    is_deduction BOOLEAN DEFAULT TRUE,  -- TRUE for deductions, FALSE for bonuses/additions
    is_mandatory BOOLEAN DEFAULT FALSE,  -- Mandatory vs optional
    is_taxable BOOLEAN DEFAULT FALSE,   -- Whether this affects net salary calculation
    is_percentage_based BOOLEAN DEFAULT FALSE,  -- Can be applied as percentage
    is_fixed_amount BOOLEAN DEFAULT FALSE,      -- Can be applied as fixed amount

    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,
    updated_by UUID,

    CONSTRAINT uq_deduction_type_per_tenant UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_deduction_types_tenant ON deduction_types(tenant_id);
CREATE INDEX IF NOT EXISTS ix_deduction_types_code ON deduction_types(code);
CREATE INDEX IF NOT EXISTS ix_deduction_types_active ON deduction_types(is_active);

-- ============================================================================
-- Gender Types
-- ============================================================================
-- Gender/social classification codes for employees
CREATE TABLE IF NOT EXISTS gender_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    name_es VARCHAR(100),
    name_pt VARCHAR(100),
    description_en TEXT,
    description_es TEXT,
    description_pt TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,
    updated_by UUID,

    CONSTRAINT uq_gender_type_per_tenant UNIQUE(tenant_id, code)
);

CREATE INDEX IF NOT EXISTS ix_gender_types_tenant ON gender_types(tenant_id);
CREATE INDEX IF NOT EXISTS ix_gender_types_code ON gender_types(code);
CREATE INDEX IF NOT EXISTS ix_gender_types_active ON gender_types(is_active);

COMMIT;
