BEGIN;

ALTER TABLE public.import_column_mappings
    DROP COLUMN IF EXISTS transforms,
    DROP COLUMN IF EXISTS defaults;

COMMIT;
