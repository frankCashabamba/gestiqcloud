-- Migration: 2026-03-17_001_branches
-- Creates the branches table and links warehouses, pos_registers, pos_shifts, company_user_roles.
-- Idempotente: usa IF NOT EXISTS / DO $$ blocks.

CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    phone VARCHAR(20),
    is_main BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Unique code per tenant
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'uq_branches_tenant_code') THEN
        CREATE UNIQUE INDEX uq_branches_tenant_code ON branches(tenant_id, code);
    END IF;
END $$;

-- RLS
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'branches_tenant_isolation') THEN
        CREATE POLICY branches_tenant_isolation ON branches
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
    END IF;
END $$;

-- Add branch_id to existing tables
ALTER TABLE warehouses ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id);
ALTER TABLE pos_registers ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id);
ALTER TABLE pos_shifts ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id);
ALTER TABLE company_user_roles ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(id);

-- Indexes
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_warehouses_branch_id') THEN
        CREATE INDEX ix_warehouses_branch_id ON warehouses(branch_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_pos_registers_branch_id') THEN
        CREATE INDEX ix_pos_registers_branch_id ON pos_registers(branch_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_pos_shifts_branch_id') THEN
        CREATE INDEX ix_pos_shifts_branch_id ON pos_shifts(branch_id);
    END IF;
END $$;
