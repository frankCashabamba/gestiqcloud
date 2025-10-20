# Migration: 2025-10-20_104_migrate_products_to_tenant_uuid

## Description
Migrates the `products` table from legacy multi-tenant using `empresa_id` (int) to UUID-based multi-tenant using `tenant_id` (UUID).

This completes the transition for products, following the same pattern as invoices migration.

## Changes
- Drops old RLS policy and empresa_id related constraints/indexes
- Removes `empresa_id` column
- Recreates RLS policy using `tenant_id`
- Maintains tenant_id index

## Rollback
The `down.sql` reverts back to `empresa_id` multi-tenant setup.

## Prerequisites
- `tenants` table must exist and be populated
- Products must have tenant_id populated (from previous migration 2025-10-09_010)

## Post-migration
- Update Product model to remove empresa_id field
- Update any remaining code references from empresa_id to tenant_id
- Test product CRUD operations
