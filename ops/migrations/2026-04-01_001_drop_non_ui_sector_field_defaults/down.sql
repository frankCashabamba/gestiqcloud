-- Drop the DB-backed deny rules.
-- Note: removed legacy rows from sector_field_defaults are not recreated here.

BEGIN;

DROP TABLE IF EXISTS ui_field_config_scope_rules;

COMMIT;
