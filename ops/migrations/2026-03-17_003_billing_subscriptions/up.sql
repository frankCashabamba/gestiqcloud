-- Migration: 2026-03-17_003_billing_subscriptions
-- Creates subscription plans and tenant subscriptions for SaaS billing.
-- Idempotente.

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    price_monthly NUMERIC(10, 2) NOT NULL DEFAULT 0,
    price_yearly NUMERIC(10, 2),
    max_users INT DEFAULT 1,
    max_branches INT DEFAULT 1,
    included_modules TEXT[] DEFAULT '{}',
    features JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    stripe_price_id_monthly VARCHAR(100),
    stripe_price_id_yearly VARCHAR(100),
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    status VARCHAR(20) DEFAULT 'trialing',
    billing_cycle VARCHAR(10) DEFAULT 'monthly',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    stripe_subscription_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    canceled_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_tenant_subscriptions_tenant') THEN
        CREATE INDEX ix_tenant_subscriptions_tenant ON tenant_subscriptions(tenant_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'uq_tenant_subscriptions_active') THEN
        CREATE UNIQUE INDEX uq_tenant_subscriptions_active ON tenant_subscriptions(tenant_id)
            WHERE status IN ('active', 'trialing');
    END IF;
END $$;

ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_subscriptions_tenant_isolation') THEN
        CREATE POLICY tenant_subscriptions_tenant_isolation ON tenant_subscriptions
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
    END IF;
END $$;

-- Seed default plans
INSERT INTO subscription_plans (name, display_name, price_monthly, price_yearly, max_users, max_branches, included_modules, features, sort_order)
VALUES
    ('starter', 'Starter', 29.99, 299.90, 3, 1,
     '{products,pos,inventory,clients}',
     '{"ai_chat": false, "reports": false, "einvoicing": false}',
     1),
    ('professional', 'Professional', 79.99, 799.90, 10, 3,
     '{products,pos,inventory,clients,purchases,sales,expenses,reports,production}',
     '{"ai_chat": true, "reports": true, "einvoicing": false}',
     2),
    ('enterprise', 'Enterprise', 199.99, 1999.90, 50, 10,
     '{products,pos,inventory,clients,purchases,sales,expenses,reports,production,accounting,hr,einvoicing,crm}',
     '{"ai_chat": true, "reports": true, "einvoicing": true, "api_access": true}',
     3)
ON CONFLICT DO NOTHING;
