-- Migration: 2026-01-14_000_add_global_permissions_module
-- Description: Add module column to global_action_permissions and backfill.

BEGIN;

ALTER TABLE global_action_permissions
    ADD COLUMN IF NOT EXISTS module VARCHAR(50);

UPDATE global_action_permissions
SET module = split_part(key, '.', 1)
WHERE module IS NULL AND key LIKE '%.%';

COMMIT;
