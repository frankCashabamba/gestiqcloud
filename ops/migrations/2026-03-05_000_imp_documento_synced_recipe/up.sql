ALTER TABLE imp_documento
  ADD COLUMN IF NOT EXISTS synced_recipe_id UUID NULL;

COMMENT ON COLUMN imp_documento.synced_recipe_id IS 'ID de la receta de produccion creada/actualizada desde este documento';
