-- ============================================================================
-- Migration: 2025-11-18_300_suppliers_system
-- Description: Suppliers management system (suppliers, contacts, addresses)
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
-- Table: suppliers
-- ============================================================================

CREATE TABLE IF NOT EXISTS suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    -- Basic info
    code VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    trade_name VARCHAR(255),
    tax_id VARCHAR(50),

    -- Contact
    email VARCHAR(254),
    phone VARCHAR(20),
    website VARCHAR(255),

    -- Configuration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,

    -- Notes
    notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT suppliers_tenant_code_unique UNIQUE (tenant_id, code)
);

CREATE INDEX IF NOT EXISTS idx_suppliers_tenant ON suppliers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_suppliers_code ON suppliers(code);
CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name);
CREATE INDEX IF NOT EXISTS idx_suppliers_is_active ON suppliers(is_active) WHERE is_active = TRUE;

COMMENT ON TABLE suppliers IS 'Supplier/vendor records';
COMMENT ON COLUMN suppliers.code IS 'Supplier code';
COMMENT ON COLUMN suppliers.trade_name IS 'Trade name / commercial name';
COMMENT ON COLUMN suppliers.tax_id IS 'Tax identification number';

ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_suppliers ON suppliers;
CREATE POLICY tenant_isolation_suppliers ON suppliers
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- ============================================================================
-- Table: supplier_contacts
-- ============================================================================

CREATE TABLE IF NOT EXISTS supplier_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,

    -- Contact info
    name VARCHAR(255) NOT NULL,
    position VARCHAR(100),
    email VARCHAR(254),
    phone VARCHAR(20),

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_supplier_contacts_supplier ON supplier_contacts(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_contacts_email ON supplier_contacts(email);

COMMENT ON TABLE supplier_contacts IS 'Contact persons for suppliers';
COMMENT ON COLUMN supplier_contacts.position IS 'Job position/title';

-- ============================================================================
-- Table: supplier_addresses
-- ============================================================================

CREATE TABLE IF NOT EXISTS supplier_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,

    -- Address info
    type VARCHAR(50) DEFAULT 'BILLING',  -- BILLING, SHIPPING, etc.
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100),

    -- Configuration
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT supplier_addresses_supplier_type_unique UNIQUE (supplier_id, type)
);

CREATE INDEX IF NOT EXISTS idx_supplier_addresses_supplier ON supplier_addresses(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_addresses_type ON supplier_addresses(type);
CREATE INDEX IF NOT EXISTS idx_supplier_addresses_is_primary ON supplier_addresses(is_primary) WHERE is_primary = TRUE;

COMMENT ON TABLE supplier_addresses IS 'Supplier addresses (billing, shipping, etc.)';
COMMENT ON COLUMN supplier_addresses.type IS 'Address type: BILLING, SHIPPING, HEADQUARTERS, etc.';

-- ============================================================================
-- Triggers
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'suppliers_updated_at'
    ) THEN
        CREATE TRIGGER suppliers_updated_at
            BEFORE UPDATE ON suppliers
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'supplier_contacts_updated_at'
    ) THEN
        CREATE TRIGGER supplier_contacts_updated_at
            BEFORE UPDATE ON supplier_contacts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'supplier_addresses_updated_at'
    ) THEN
        CREATE TRIGGER supplier_addresses_updated_at
            BEFORE UPDATE ON supplier_addresses
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;

COMMIT;
