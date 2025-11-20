-- =====================================================
-- VALIDATION SCRIPT: Verify Migration Completeness
-- =====================================================

-- Display current date/time
SELECT 'Migration Validation Started at: ' || NOW();

-- =====================================================
-- 1. Check if Spanish tables still exist (should be gone)
-- =====================================================
\echo '=== CHECKING FOR OLD SPANISH TABLES (should be empty) ==='
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'proveedores', 'proveedor_contactos', 'proveedor_direcciones',
    'compras', 'compra_lineas', 'ventas',
    'gastos', 'banco_movimientos', 'nominas', 'nomina_conceptos', 'nomina_plantillas',
    'modulos_modulo', 'modulos_empresamodulo', 'modulos_moduloasignado',
    'usuarios_usuariorolempresa', 'usuarios_usuarioempresa',
    'core_configuracionempresa', 'core_configuracioninventarioempresa',
    'core_rolempresa', 'core_tipoempresa', 'core_tiponegocio', 'core_moneda',
    'lineas_panaderia', 'lineas_taller', 'facturas_temp',
    'auditoria_importacion'
);

-- =====================================================
-- 2. Check if English tables exist (should show all)
-- =====================================================
\echo '\n=== CHECKING FOR NEW ENGLISH TABLES (should show all created) ==='
WITH expected_tables AS (
    SELECT 'suppliers' AS table_name
    UNION ALL SELECT 'supplier_contacts'
    UNION ALL SELECT 'supplier_addresses'
    UNION ALL SELECT 'purchases'
    UNION ALL SELECT 'purchase_lines'
    UNION ALL SELECT 'sales'
    UNION ALL SELECT 'expenses'
    UNION ALL SELECT 'bank_movements'
    UNION ALL SELECT 'payrolls'
    UNION ALL SELECT 'payroll_items'
    UNION ALL SELECT 'payroll_templates'
    UNION ALL SELECT 'modules'
    UNION ALL SELECT 'company_modules'
    UNION ALL SELECT 'assigned_modules'
    UNION ALL SELECT 'user_company_roles'
    UNION ALL SELECT 'user_companies'
    UNION ALL SELECT 'company_settings'
    UNION ALL SELECT 'company_inventory_settings'
    UNION ALL SELECT 'company_roles'
    UNION ALL SELECT 'company_types'
    UNION ALL SELECT 'business_types'
    UNION ALL SELECT 'currencies_legacy'
    UNION ALL SELECT 'bakery_lines'
    UNION ALL SELECT 'workshop_lines'
    UNION ALL SELECT 'invoices_temp'
    UNION ALL SELECT 'import_audit'
)
SELECT
    et.table_name,
    CASE WHEN it.table_name IS NOT NULL THEN '✓ EXISTS' ELSE '✗ MISSING' END AS status
FROM expected_tables et
LEFT JOIN information_schema.tables it
    ON et.table_name = it.table_name
    AND it.table_schema = 'public'
ORDER BY et.table_name;

-- =====================================================
-- 3. Check key columns in main tables
-- =====================================================
\echo '\n=== CHECKING COLUMN RENAMES (suppliers table) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'suppliers'
ORDER BY ordinal_position;

\echo '\n=== CHECKING COLUMN RENAMES (purchases table) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'purchases'
ORDER BY ordinal_position;

\echo '\n=== CHECKING COLUMN RENAMES (expenses table) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'expenses'
ORDER BY ordinal_position;

\echo '\n=== CHECKING COLUMN RENAMES (bank_movements table) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'bank_movements'
ORDER BY ordinal_position;

\echo '\n=== CHECKING COLUMN RENAMES (payrolls table) ==='
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'payrolls'
ORDER BY ordinal_position;

-- =====================================================
-- 4. Check Foreign Key Constraints
-- =====================================================
\echo '\n=== CHECKING FOREIGN KEY CONSTRAINTS ==='
SELECT
    constraint_name,
    table_name,
    column_name,
    referenced_table_name,
    referenced_column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public'
    AND referenced_table_name IS NOT NULL
    AND table_name IN ('suppliers', 'purchases', 'sales', 'expenses', 'payrolls', 'supplier_contacts', 'supplier_addresses')
ORDER BY table_name, constraint_name;

-- =====================================================
-- 5. Table Row Counts (should not be 0 if data was preserved)
-- =====================================================
\echo '\n=== TABLE ROW COUNTS ==='
SELECT
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
    AND tablename IN ('suppliers', 'purchases', 'sales', 'expenses', 'bank_movements', 'payrolls')
ORDER BY tablename;

-- =====================================================
-- 6. Validation Summary
-- =====================================================
\echo '\n=== VALIDATION SUMMARY ==='
SELECT 'Migration validation completed at: ' || NOW();
SELECT 'Review the results above to ensure:';
SELECT '  1. No Spanish table names exist';
SELECT '  2. All English tables are created';
SELECT '  3. All columns are properly named';
SELECT '  4. Foreign keys are correctly configured';
SELECT '  5. Data row counts are as expected';
