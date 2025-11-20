-- =====================================================
-- CORE BUSINESS TABLES: Clients, Invoices, Invoice Lines
-- Migration: 2025-11-01_110_core_business_tables
-- =====================================================

BEGIN;

-- =====================================================
-- CLIENTS: Customer/Client Records
-- =====================================================
CREATE TABLE IF NOT EXISTS clients (
    id UUID DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    tax_id VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    address VARCHAR,
    city VARCHAR,
    state VARCHAR,
    country VARCHAR,
    postal_code VARCHAR,
    tenant_id UUID,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX IF NOT EXISTS idx_clients_id ON clients(id);
CREATE INDEX IF NOT EXISTS idx_clients_tenant_id ON clients(tenant_id);

-- =====================================================
-- INVOICES: Invoice Headers
-- =====================================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID DEFAULT gen_random_uuid(),
    number VARCHAR NOT NULL,
    supplier VARCHAR NOT NULL,
    issue_date VARCHAR NOT NULL,
    amount INTEGER NOT NULL DEFAULT 0,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at VARCHAR NOT NULL DEFAULT NOW(),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    subtotal FLOAT NOT NULL,
    vat FLOAT NOT NULL,
    total FLOAT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (customer_id) REFERENCES clients(id)
);

CREATE INDEX IF NOT EXISTS idx_invoices_id ON invoices(id);
CREATE INDEX IF NOT EXISTS idx_invoices_tenant_id ON invoices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer_id ON invoices(customer_id);

-- =====================================================
-- INVOICE_LINES: Invoice Line Items
-- =====================================================
CREATE TABLE IF NOT EXISTS invoice_lines (
    id UUID DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL,
    sector VARCHAR(50) NOT NULL,
    description VARCHAR NOT NULL,
    quantity FLOAT NOT NULL,
    unit_price FLOAT NOT NULL,
    vat FLOAT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);

CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id);

COMMIT;
