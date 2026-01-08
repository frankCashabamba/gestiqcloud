-- Migration: Create audit_events table (global audit log)
-- Date: 2026-01-15
-- Purpose: Unified audit log for all modules/actions

BEGIN;

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NULL,
    user_id UUID NULL,
    actor_type VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NULL,
    source VARCHAR(20) NOT NULL,
    changes JSONB NULL,
    ip VARCHAR(45) NULL,
    ua TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_tenant_id ON audit_events(tenant_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_entity ON audit_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_action ON audit_events(action);
CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events(created_at);

COMMIT;
