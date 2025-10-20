-- Create table for logging sync conflict resolutions

CREATE TABLE IF NOT EXISTS sync_conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,  -- 'products', 'stock_items', 'pos_receipts', etc.
    entity_id TEXT NOT NULL,    -- ID of the conflicting entity
    conflict_data JSONB,        -- Original conflict details
    resolution TEXT,            -- Resolution strategy used
    resolved_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes for efficient querying
    INDEX idx_sync_conflicts_tenant (tenant_id),
    INDEX idx_sync_conflicts_entity (entity_type, entity_id),
    INDEX idx_sync_conflicts_resolved_at (resolved_at)
);

-- Enable RLS for tenant isolation
ALTER TABLE sync_conflict_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON sync_conflict_log
  USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT ON sync_conflict_log TO authenticated_user;
