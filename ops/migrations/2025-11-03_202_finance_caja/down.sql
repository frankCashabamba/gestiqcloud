-- ============================================================================
-- Migration Rollback: 2025-11-03_202_finance_caja
-- Descripción: Rollback del sistema de gestión de caja
-- ============================================================================

-- Eliminar vistas
DROP VIEW IF EXISTS v_caja_resumen_diario CASCADE;

-- Eliminar triggers
DROP TRIGGER IF EXISTS caja_movimientos_actualizar_cierre ON caja_movimientos;
DROP TRIGGER IF EXISTS cierres_caja_updated_at ON cierres_caja;

-- Eliminar funciones
DROP FUNCTION IF EXISTS trigger_actualizar_cierre_movimiento();
DROP FUNCTION IF EXISTS recalcular_totales_cierre(UUID);

-- Eliminar políticas RLS
DROP POLICY IF EXISTS caja_movimientos_tenant_isolation ON caja_movimientos;
DROP POLICY IF EXISTS cierres_caja_tenant_isolation ON cierres_caja;

-- Eliminar tablas (en orden inverso por dependencias)
DROP TABLE IF EXISTS caja_movimientos CASCADE;
DROP TABLE IF EXISTS cierres_caja CASCADE;

-- Eliminar tipos ENUM
DROP TYPE IF EXISTS cierre_caja_status CASCADE;
DROP TYPE IF EXISTS caja_movimiento_categoria CASCADE;
DROP TYPE IF EXISTS caja_movimiento_tipo CASCADE;

-- Log de rollback
DO $$
BEGIN
    RAISE NOTICE 'Rollback de migración 2025-11-03_202_finance_caja completado';
END $$;
