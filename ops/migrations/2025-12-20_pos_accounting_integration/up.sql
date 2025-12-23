-- Crear tablas de configuración contable para POS
CREATE TABLE IF NOT EXISTS tenant_accounting_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL UNIQUE REFERENCES tenants(id) ON DELETE CASCADE,
    cash_account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    bank_account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    sales_bakery_account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    vat_output_account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    loss_account_id UUID NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    account_id UUID NOT NULL REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT uq_payment_methods_tenant_name UNIQUE (tenant_id, name)
);
