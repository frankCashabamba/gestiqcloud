-- ============================================================================
-- Migration: 2025-11-18_340_business_reference_tables
-- Description: Business configuration and reference tables
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
-- Table: business_types
-- ============================================================================

CREATE TABLE IF NOT EXISTS business_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Basic info
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT business_types_tenant_code_unique UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_business_types_tenant ON business_types(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_types_code ON business_types(code);

COMMENT ON TABLE business_types IS 'Types of businesses (retail, service, manufacturing, etc.)';

-- ============================================================================
-- Table: business_categories
-- ============================================================================

CREATE TABLE IF NOT EXISTS business_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Basic info
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT business_categories_tenant_code_unique UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_business_categories_tenant ON business_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_categories_code ON business_categories(code);

COMMENT ON TABLE business_categories IS 'Categories for business classification';

-- ============================================================================
-- Table: company_categories
-- ============================================================================

CREATE TABLE IF NOT EXISTS company_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Basic info
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT company_categories_tenant_code_unique UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_company_categories_tenant ON company_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_company_categories_code ON company_categories(code);

COMMENT ON TABLE company_categories IS 'Company categories for organization';

-- ============================================================================
-- Table: business_hours
-- ============================================================================

CREATE TABLE IF NOT EXISTS business_hours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Day and hours
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    opens_at TIME NOT NULL,
    closes_at TIME NOT NULL,

    -- Configuration
    is_open BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT business_hours_tenant_day_unique UNIQUE (tenant_id, day_of_week)
);

CREATE INDEX IF NOT EXISTS idx_business_hours_tenant ON business_hours(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_hours_day ON business_hours(day_of_week);

COMMENT ON TABLE business_hours IS 'Business operating hours by day of week';
COMMENT ON COLUMN business_hours.day_of_week IS '0=Sunday, 1=Monday, ..., 6=Saturday';

-- ============================================================================
-- Table: user_profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES company_users(id) ON DELETE CASCADE,

    -- Profile info
    bio TEXT,
    avatar_url VARCHAR(500),
    phone VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    -- Preferences
    timezone VARCHAR(50),
    locale VARCHAR(10),
    theme VARCHAR(20),

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT user_profiles_tenant_user_unique UNIQUE (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_tenant ON user_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id);

COMMENT ON TABLE user_profiles IS 'Extended user profile information';

-- ============================================================================
-- Table: sector_templates
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Basic info
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    template_config JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT sector_templates_tenant_code_unique UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_sector_templates_tenant ON sector_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sector_templates_code ON sector_templates(code);

COMMENT ON TABLE sector_templates IS 'Sector-specific templates and configurations';
COMMENT ON COLUMN sector_templates.template_config IS 'Template configuration in JSON format';

-- ============================================================================
-- Table: sector_field_defaults
-- ============================================================================

CREATE TABLE IF NOT EXISTS sector_field_defaults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sector_template_id UUID REFERENCES sector_templates(id) ON DELETE CASCADE,

    -- Field mapping
    field_name VARCHAR(100) NOT NULL,
    field_type VARCHAR(50),
    default_value TEXT,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sector_field_defaults_tenant ON sector_field_defaults(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sector_field_defaults_template ON sector_field_defaults(sector_template_id);

COMMENT ON TABLE sector_field_defaults IS 'Default field values and configurations per sector';

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'business_types_updated_at'
    ) THEN
        CREATE TRIGGER business_types_updated_at
            BEFORE UPDATE ON business_types
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'business_categories_updated_at'
    ) THEN
        CREATE TRIGGER business_categories_updated_at
            BEFORE UPDATE ON business_categories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'company_categories_updated_at'
    ) THEN
        CREATE TRIGGER company_categories_updated_at
            BEFORE UPDATE ON company_categories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'business_hours_updated_at'
    ) THEN
        CREATE TRIGGER business_hours_updated_at
            BEFORE UPDATE ON business_hours
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'user_profiles_updated_at'
    ) THEN
        CREATE TRIGGER user_profiles_updated_at
            BEFORE UPDATE ON user_profiles
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'sector_templates_updated_at'
    ) THEN
        CREATE TRIGGER sector_templates_updated_at
            BEFORE UPDATE ON sector_templates
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'sector_field_defaults_updated_at'
    ) THEN
        CREATE TRIGGER sector_field_defaults_updated_at
            BEFORE UPDATE ON sector_field_defaults
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
