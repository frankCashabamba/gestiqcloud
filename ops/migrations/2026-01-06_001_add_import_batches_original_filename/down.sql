BEGIN;

ALTER TABLE public.import_batches
    DROP COLUMN IF EXISTS original_filename;

COMMIT;
