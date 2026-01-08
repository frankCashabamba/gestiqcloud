-- Migration: 2026-01-14_000_add_global_permissions_module
-- Description: Remove module column from global_action_permissions.

BEGIN;

ALTER TABLE global_action_permissions
    DROP COLUMN IF EXISTS module;

COMMIT;
