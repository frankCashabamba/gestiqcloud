-- Migration: 2026-01-13_000_crm_tables
-- Description: Create CRM tables and enum types.

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadstatus') THEN
        CREATE TYPE leadstatus AS ENUM (
            'new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leadsource') THEN
        CREATE TYPE leadsource AS ENUM (
            'website', 'referral', 'social_media', 'email', 'phone', 'event', 'other'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'opportunitystage') THEN
        CREATE TYPE opportunitystage AS ENUM (
            'qualification', 'needs_analysis', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activitytype') THEN
        CREATE TYPE activitytype AS ENUM (
            'call', 'email', 'meeting', 'task', 'note', 'other'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'activitystatus') THEN
        CREATE TYPE activitystatus AS ENUM (
            'pending', 'completed', 'cancelled', 'overdue'
        );
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS crm_leads (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    email VARCHAR(200) NOT NULL,
    phone VARCHAR(50),
    status leadstatus NOT NULL DEFAULT 'new',
    source leadsource NOT NULL DEFAULT 'other',
    assigned_to UUID REFERENCES company_users(id) ON DELETE SET NULL,
    score INTEGER,
    notes TEXT,
    custom_fields JSONB,
    converted_at TIMESTAMPTZ,
    opportunity_id UUID,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_crm_leads_tenant_id ON crm_leads(tenant_id);
CREATE INDEX IF NOT EXISTS idx_crm_leads_status ON crm_leads(status);
CREATE INDEX IF NOT EXISTS idx_crm_leads_created_at ON crm_leads(created_at);

CREATE TABLE IF NOT EXISTS crm_opportunities (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES crm_leads(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    value NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
    probability INTEGER NOT NULL DEFAULT 50,
    stage opportunitystage NOT NULL DEFAULT 'qualification',
    expected_close_date TIMESTAMPTZ,
    actual_close_date TIMESTAMPTZ,
    assigned_to UUID REFERENCES company_users(id) ON DELETE SET NULL,
    lost_reason TEXT,
    custom_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_crm_opportunities_tenant_id ON crm_opportunities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_crm_opportunities_stage ON crm_opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_crm_opportunities_lead_id ON crm_opportunities(lead_id);
CREATE INDEX IF NOT EXISTS idx_crm_opportunities_customer_id ON crm_opportunities(customer_id);
CREATE INDEX IF NOT EXISTS idx_crm_opportunities_created_at ON crm_opportunities(created_at);

CREATE TABLE IF NOT EXISTS crm_activities (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES crm_leads(id) ON DELETE SET NULL,
    opportunity_id UUID REFERENCES crm_opportunities(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    type activitytype NOT NULL DEFAULT 'note',
    subject VARCHAR(300) NOT NULL,
    description TEXT,
    status activitystatus NOT NULL DEFAULT 'pending',
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    assigned_to UUID REFERENCES company_users(id) ON DELETE SET NULL,
    created_by UUID REFERENCES company_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_crm_activities_tenant_id ON crm_activities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_crm_activities_lead_id ON crm_activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_crm_activities_opportunity_id ON crm_activities(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_crm_activities_customer_id ON crm_activities(customer_id);
CREATE INDEX IF NOT EXISTS idx_crm_activities_status ON crm_activities(status);
CREATE INDEX IF NOT EXISTS idx_crm_activities_due_date ON crm_activities(due_date);
CREATE INDEX IF NOT EXISTS idx_crm_activities_created_at ON crm_activities(created_at);

COMMIT;
