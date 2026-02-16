-- Revert: This migration deletes data, so rollback would need to restore from backup
-- No practical rollback available - deletion cannot be undone without a backup

-- If needed, the modules can be recreated using:
-- INSERT INTO modules (id, name, url, active, icon, category, initial_template, context_type) VALUES
-- ('d2dd675b-4185-4573-800c-3360fc0ac5d4', 'Compras', NULL, false, NULL, NULL, 'Compras', 'none'),
-- ('0d7947bf-dc63-4e42-9890-2002fe5a4644', 'Ventas', NULL, false, NULL, NULL, 'Ventas', 'none'),
-- ('44310dd9-0e0c-4c5b-8ef2-bd60c01b3b7c', 'Facturacion', NULL, false, NULL, NULL, 'Facturacion', 'none');
