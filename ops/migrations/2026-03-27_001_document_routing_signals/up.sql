CREATE TABLE IF NOT EXISTS imp_routing_signal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    documento_id UUID NOT NULL REFERENCES imp_documento(id) ON DELETE CASCADE,
    event VARCHAR(30) NOT NULL,
    user_id VARCHAR(100),
    chosen_destination VARCHAR(30),
    changed_fields JSONB,
    routing_snapshot JSONB NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_imp_routing_signal_tenant
    ON imp_routing_signal (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_imp_routing_signal_document
    ON imp_routing_signal (documento_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_imp_routing_signal_event
    ON imp_routing_signal (event, created_at DESC);
