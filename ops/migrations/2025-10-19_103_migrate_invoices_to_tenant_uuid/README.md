# Migration: 2025-10-19_103_migrate_invoices_to_tenant_uuid

## Description
Migrates the `facturas` (invoices) table from legacy multi-tenant using `empresa_id` (int) to UUID-based multi-tenant using `tenant_id` (UUID).

This is part of M3 roadmap: Full UUID multi-tenant end-to-end, deprecating empresa_id in favor of tenant_id.

## Changes
- Adds `tenant_id UUID` column
- Backfills `tenant_id` from `tenants` table using existing `empresa_id`
- Sets `tenant_id` as NOT NULL with FK to `tenants(id)`
- Drops `empresa_id` column
- Recreates RLS policy to use `tenant_id`
- Adds index on `tenant_id` for performance

## Rollback
The `down.sql` reverts back to `empresa_id` multi-tenant setup.

## Prerequisites
- `tenants` table must exist and be populated with correct `empresa_id` mappings
- No active transactions on `facturas` during migration

## Post-migration
- Update any remaining code references from `empresa_id` to `tenant_id` in models/routers if not already done
- Test RLS policies and tenant isolation
