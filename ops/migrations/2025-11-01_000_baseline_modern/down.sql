-- =====================================================
-- ROLLBACK BASELINE MODERNA
-- =====================================================
-- ADVERTENCIA: Esto eliminará TODAS las tablas del sistema
-- excepto auth_user y modulos_*
-- =====================================================

BEGIN;

-- Desactivar foreign keys temporalmente
SET session_replication_role = 'replica';

-- Drop functions
DROP FUNCTION IF EXISTS check_low_stock() CASCADE;

-- Drop tables en orden inverso (por dependencias)
DROP TABLE IF EXISTS pos_payments CASCADE;
DROP TABLE IF EXISTS pos_receipt_lines CASCADE;
DROP TABLE IF EXISTS pos_receipts CASCADE;
DROP TABLE IF EXISTS pos_shifts CASCADE;
DROP TABLE IF EXISTS pos_registers CASCADE;

DROP TABLE IF EXISTS stock_alerts CASCADE;
DROP TABLE IF EXISTS stock_moves CASCADE;
DROP TABLE IF EXISTS stock_items CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;

DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS product_categories CASCADE;

DROP TABLE IF NOT EXISTS tenants CASCADE;

-- Reactivar foreign keys
SET session_replication_role = 'origin';

COMMIT;
