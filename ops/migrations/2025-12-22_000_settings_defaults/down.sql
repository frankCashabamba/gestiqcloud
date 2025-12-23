-- Down migration: drop settings_defaults

BEGIN;

DROP TABLE IF EXISTS settings_defaults CASCADE;

COMMIT;
