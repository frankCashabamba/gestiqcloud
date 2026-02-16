-- Normalize all module names to English
-- The frontend will translate them using i18n via the locales/es.json file
-- 
-- This migration:
-- 1. Deactivates old duplicate Spanish modules that don't have URLs
-- 2. Renames remaining Spanish module names to English
-- 3. Works in conjunction with backend/_normalize_module_name() which ensures
--    any new modules registered from the filesystem are also normalized

-- 1. Deactivate old duplicate Spanish modules (without URLs)
UPDATE modules SET active = FALSE WHERE name IN ('Compras', 'Ventas', 'Facturacion') AND url IS NULL;

-- 2. Rename Spanish module names to English (all lowercase for consistency)
UPDATE modules SET name = 'reports' WHERE name = 'reportes';
UPDATE modules SET name = 'users' WHERE name = 'usuarios' OR name = 'Users';
UPDATE modules SET name = 'manufacturing' WHERE name = 'produccion' OR name = 'Manufacturing';

-- Verify the changes - should show 23 active modules, all with English names
-- SELECT id, name, url, active FROM modules WHERE active = TRUE ORDER BY name;
