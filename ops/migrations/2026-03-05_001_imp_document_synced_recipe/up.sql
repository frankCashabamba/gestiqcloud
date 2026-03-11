ALTER TABLE imp_documento
  ADD COLUMN IF NOT EXISTS synced_recipe_id UUID NULL;

COMMENT ON COLUMN imp_documento.synced_recipe_id IS 'ID of the production recipe created or updated from this document';
