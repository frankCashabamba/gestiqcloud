-- Rollback: Production Orders
-- Elimina tablas y tipos creados en la migración

-- 1. Eliminar trigger
DROP TRIGGER IF EXISTS trigger_update_production_order_updated_at ON production_orders;
DROP FUNCTION IF EXISTS update_production_order_updated_at();

-- 2. Eliminar políticas RLS
DROP POLICY IF EXISTS tenant_isolation ON production_order_lines;
DROP POLICY IF EXISTS tenant_isolation ON production_orders;

-- 3. Eliminar tablas (en orden inverso por FK)
DROP TABLE IF EXISTS production_order_lines CASCADE;
DROP TABLE IF EXISTS production_orders CASCADE;

-- 4. Eliminar tipo ENUM
DROP TYPE IF EXISTS production_order_status CASCADE;
