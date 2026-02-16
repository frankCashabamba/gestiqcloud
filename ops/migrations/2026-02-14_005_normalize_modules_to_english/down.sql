-- Revert: Normalize all module names to English

-- 1. Reactivate old duplicate Spanish modules
UPDATE modules SET active = TRUE WHERE name IN ('Compras', 'Ventas', 'Facturacion') AND url IS NULL;

-- 2. Rename English module names back to Spanish
UPDATE modules SET name = 'reportes' WHERE name = 'Reports' AND url = 'reportes';
UPDATE modules SET name = 'usuarios' WHERE name = 'Users' AND url = 'usuarios';
UPDATE modules SET name = 'produccion' WHERE name = 'Manufacturing' AND url = 'produccion';
