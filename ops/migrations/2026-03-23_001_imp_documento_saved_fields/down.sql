ALTER TABLE imp_documento
  DROP COLUMN IF EXISTS saved_as,
  DROP COLUMN IF EXISTS saved_record_id,
  DROP COLUMN IF EXISTS saved_at;
