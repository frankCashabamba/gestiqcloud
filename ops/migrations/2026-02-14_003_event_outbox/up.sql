-- Migration: 2026-02-14_003_event_outbox
-- Description: Event Outbox pattern — guaranteed event delivery

BEGIN;

CREATE TABLE IF NOT EXISTS event_outbox (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    aggregate_type TEXT,
    aggregate_id UUID,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    published_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    scheduled_at TIMESTAMPTZ,
    PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_event_outbox_tenant_id ON event_outbox(tenant_id);
CREATE INDEX IF NOT EXISTS ix_event_outbox_unpublished ON event_outbox(published_at) WHERE published_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_event_outbox_tenant_event_type ON event_outbox(tenant_id, event_type);
CREATE INDEX IF NOT EXISTS ix_event_outbox_created_at ON event_outbox(created_at);

COMMIT;
