-- Delete inactive duplicate Spanish modules permanently
-- These are Compras, Ventas, Facturacion (without URLs) which were deactivated in migration 005
-- They are safe to delete because:
-- 1. Their assignments have been migrated to the active English versions (purchases, sales, billing)
-- 2. They are no longer part of the active module catalog
-- 3. This prevents them from appearing in any API responses

DELETE FROM modules WHERE name IN ('Compras', 'Ventas', 'Facturacion') AND url IS NULL AND active = FALSE;

-- Verify the remaining active modules - should be 23
-- SELECT COUNT(*) FROM modules WHERE active = TRUE;
