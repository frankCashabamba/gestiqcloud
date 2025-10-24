# Migration: 2025-10-21_105_sync_conflict_log

## Description
Creates table for logging ElectricSQL sync conflict resolutions.

This table tracks all conflict resolution events during offline-first sync operations,
providing audit trail and debugging capabilities.

## Changes
- Creates `sync_conflict_log` table with tenant isolation
- Adds indexes for efficient querying
- Enables RLS with tenant_id policy
- Grants appropriate permissions

## Table Schema
```sql
sync_conflict_log (
    id UUID PRIMARY KEY,
    tenant_id UUID (FK to tenants),
    entity_type TEXT,    -- 'products', 'stock_items', etc.
    entity_id TEXT,      -- ID of conflicting entity
    conflict_data JSONB, -- Original conflict details
    resolution TEXT,     -- 'local_wins', 'remote_wins', 'merged', etc.
    resolved_at TIMESTAMPTZ
)
```

## Rollback
Drops the table and associated policies/indexes.

## Post-migration
- Conflict resolution will be automatically logged
- Monitor conflict frequency to improve sync strategies
