BEGIN;
ALTER TABLE sector_field_defaults DROP COLUMN IF EXISTS field_type;
ALTER TABLE sector_field_defaults DROP COLUMN IF EXISTS options;
ALTER TABLE sector_field_defaults DROP COLUMN IF EXISTS validation_pattern;
ALTER TABLE tenant_field_configs DROP COLUMN IF EXISTS options;
COMMIT;
