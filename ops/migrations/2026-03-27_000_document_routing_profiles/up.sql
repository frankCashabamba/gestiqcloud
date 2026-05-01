-- Configurable document routing for importador.
-- Source of truth moves from hardcoded rules to database tables.

-- Ensure pgcrypto/uuid functions are available and DEFAULT is set.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS imp_routing_profile (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                  VARCHAR(80) NOT NULL UNIQUE,
    document_type         VARCHAR(80) NOT NULL,
    description           TEXT,
    suggested_destination VARCHAR(30),
    required_groups       JSONB NOT NULL DEFAULT '[]'::jsonb,
    support_fields        JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation_fields    JSONB NOT NULL DEFAULT '[]'::jsonb,
    blocked               BOOLEAN NOT NULL DEFAULT FALSE,
    confidence_threshold  DOUBLE PRECISION NOT NULL DEFAULT 0.80,
    active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS imp_routing_rule (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    sector      VARCHAR(100),
    source_kind VARCHAR(20) NOT NULL,
    source_key  VARCHAR(80) NOT NULL,
    profile_code VARCHAR(80) NOT NULL REFERENCES imp_routing_profile(code) ON DELETE CASCADE,
    priority    INTEGER NOT NULL DEFAULT 100,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imp_routing_rule_tenant
    ON imp_routing_rule (tenant_id)
    WHERE tenant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_imp_routing_rule_sector
    ON imp_routing_rule (sector)
    WHERE tenant_id IS NULL AND sector IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_imp_routing_rule_match
    ON imp_routing_rule (source_kind, source_key, priority)
    WHERE active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_routing_rule_tenant_scope
    ON imp_routing_rule (tenant_id, source_kind, source_key)
    WHERE tenant_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_imp_routing_rule_scope
    ON imp_routing_rule (sector, source_kind, source_key)
    WHERE tenant_id IS NULL;

INSERT INTO imp_routing_profile (
    id,
    code,
    document_type,
    description,
    suggested_destination,
    required_groups,
    support_fields,
    explanation_fields,
    blocked,
    confidence_threshold
) VALUES
    (
        gen_random_uuid(),
        'supplier_invoice',
        'supplier_invoice',
        'Supplier invoices and purchase bills ready to post into purchases.',
        'supplier_invoice',
        '[["issue_date"], ["total_amount"]]'::jsonb,
        '["vendor", "vendor_tax_id", "subtotal", "tax_amount", "doc_number", "currency", "line_items"]'::jsonb,
        '["vendor", "issue_date", "subtotal", "tax_amount", "total_amount"]'::jsonb,
        FALSE,
        0.80
    ),
    (
        gen_random_uuid(),
        'expense',
        'expense',
        'Operational expenses and receipts saved into expenses.',
        'expense',
        '[["issue_date"], ["total_amount"], ["concept", "vendor", "doc_number"]]'::jsonb,
        '["tax_amount", "currency", "payment_method"]'::jsonb,
        '["concept", "vendor", "issue_date", "tax_amount", "total_amount"]'::jsonb,
        FALSE,
        0.80
    ),
    (
        gen_random_uuid(),
        'recipe',
        'recipe',
        'Recipe or costing sheets that can become production recipes.',
        'recipe',
        '[["rows", "line_items"]]'::jsonb,
        '["doc_number"]'::jsonb,
        '["rows", "line_items"]'::jsonb,
        FALSE,
        0.80
    ),
    (
        gen_random_uuid(),
        'inventory',
        'inventory',
        'Inventory documents that should remain under review.',
        NULL,
        '[["rows", "line_items"]]'::jsonb,
        '["doc_number"]'::jsonb,
        '["rows", "line_items"]'::jsonb,
        TRUE,
        0.80
    ),
    (
        gen_random_uuid(),
        'bank_statement',
        'bank_statement',
        'Bank statements requiring dedicated reconciliation flows.',
        NULL,
        '[["issue_date"], ["rows", "line_items"]]'::jsonb,
        '["currency"]'::jsonb,
        '["issue_date", "rows"]'::jsonb,
        TRUE,
        0.80
    ),
    (
        gen_random_uuid(),
        'payroll',
        'payroll',
        'Payroll documents requiring human review.',
        NULL,
        '[["issue_date"], ["rows", "line_items"]]'::jsonb,
        '["total_amount"]'::jsonb,
        '["issue_date", "rows", "total_amount"]'::jsonb,
        TRUE,
        0.80
    ),
    (
        gen_random_uuid(),
        'other',
        'expense',
        'Fallback route when a document is not clearly classified.',
        'expense',
        '[["issue_date"], ["total_amount"]]'::jsonb,
        '["concept", "vendor", "tax_amount"]'::jsonb,
        '["concept", "vendor", "issue_date", "total_amount"]'::jsonb,
        FALSE,
        0.80
    )
ON CONFLICT (code) DO UPDATE SET
    document_type = EXCLUDED.document_type,
    description = EXCLUDED.description,
    suggested_destination = EXCLUDED.suggested_destination,
    required_groups = EXCLUDED.required_groups,
    support_fields = EXCLUDED.support_fields,
    explanation_fields = EXCLUDED.explanation_fields,
    blocked = EXCLUDED.blocked,
    confidence_threshold = EXCLUDED.confidence_threshold,
    active = TRUE,
    updated_at = now();

INSERT INTO imp_routing_rule (tenant_id, sector, source_kind, source_key, profile_code, priority) VALUES
    (NULL, '_system', 'category', 'invoice', 'supplier_invoice', 10),
    (NULL, '_system', 'category', 'receipt', 'expense', 10),
    (NULL, '_system', 'category', 'recipe', 'recipe', 10),
    (NULL, '_system', 'category', 'inventory', 'inventory', 10),
    (NULL, '_system', 'category', 'bank', 'bank_statement', 10),
    (NULL, '_system', 'category', 'payroll', 'payroll', 10),
    (NULL, '_system', 'category', 'other', 'other', 10),
    (NULL, '_system', 'doc_type', 'OTHER', 'other', 10)
ON CONFLICT DO NOTHING;
