-- Migration: 2026-01-17_001_sync_conflict_log
-- Description: Create sync_conflict_log table for ElectricSQL conflict resolution.
-- This table stores conflict resolution logs for offline-first sync operations.

BEGIN;

-- Create sync_conflict_log table
CREATE TABLE IF NOT EXISTS public.sync_conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    conflict_data JSONB,
    resolution TEXT,
    resolved_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_sync_conflicts_tenant
    ON public.sync_conflict_log(tenant_id);

CREATE INDEX IF NOT EXISTS idx_sync_conflicts_entity
    ON public.sync_conflict_log(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_sync_conflicts_resolved_at
    ON public.sync_conflict_log(resolved_at DESC);

-- Add comment for documentation
COMMENT ON TABLE public.sync_conflict_log IS
    'Logs conflict resolutions during ElectricSQL sync operations for audit purposes';

COMMIT;
