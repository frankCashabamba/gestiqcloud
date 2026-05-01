-- Migration: 2026-05-01_004_quotes
-- Description: Create `quotes` table (commercial proposals / presupuestos).
--              Lines are stored as JSONB to keep the schema simple. Conversion
--              to a SalesOrder is tracked via `converted_to_order_id`.

BEGIN;

CREATE TABLE IF NOT EXISTS quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    number VARCHAR(50),
    customer_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    lines JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total NUMERIC(12, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3),
    quote_date DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE,
    notes TEXT,
    converted_to_order_id UUID,
    created_by UUID,
    approved_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT quotes_status_chk CHECK (
        status IN ('DRAFT', 'APPROVED', 'CONVERTED', 'REJECTED', 'EXPIRED', 'CANCELLED')
    )
);

CREATE INDEX IF NOT EXISTS ix_quotes_tenant_id ON quotes(tenant_id);
CREATE INDEX IF NOT EXISTS ix_quotes_tenant_status ON quotes(tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_quotes_tenant_customer ON quotes(tenant_id, customer_id);
CREATE INDEX IF NOT EXISTS ix_quotes_tenant_number ON quotes(tenant_id, number);
CREATE INDEX IF NOT EXISTS ix_quotes_converted_order ON quotes(converted_to_order_id);

-- RLS: align with the rest of the schema (see 2026-03-14_002_comprehensive_rls).
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rls_quotes_select ON quotes;
CREATE POLICY rls_quotes_select ON quotes
    FOR SELECT
    USING (
        tenant_id::text = current_setting('app.tenant_id', true)
        OR current_setting('app.admin_bypass', true) = 'on'
    );

DROP POLICY IF EXISTS rls_quotes_modify ON quotes;
CREATE POLICY rls_quotes_modify ON quotes
    FOR ALL
    USING (
        tenant_id::text = current_setting('app.tenant_id', true)
        OR current_setting('app.admin_bypass', true) = 'on'
    )
    WITH CHECK (
        tenant_id::text = current_setting('app.tenant_id', true)
        OR current_setting('app.admin_bypass', true) = 'on'
    );

COMMIT;
