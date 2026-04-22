-- Supplier ahora hereda de BaseCatalogModel que incluye description.
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS description TEXT;
