-- ============================================================================
-- Migration Rollback: 2025-11-03_201_hr_nominas
-- Descripción: Rollback del sistema de nóminas
-- ============================================================================

-- Eliminar triggers
DROP TRIGGER IF EXISTS nominas_updated_at ON nominas;
DROP TRIGGER IF EXISTS nomina_plantillas_updated_at ON nomina_plantillas;
DROP TRIGGER IF EXISTS nominas_validate_totals ON nominas;

-- Eliminar funciones
DROP FUNCTION IF EXISTS validate_nomina_totals();

-- Eliminar políticas RLS
DROP POLICY IF EXISTS nominas_tenant_isolation ON nominas;
DROP POLICY IF EXISTS nomina_conceptos_tenant_isolation ON nomina_conceptos;
DROP POLICY IF EXISTS nomina_plantillas_tenant_isolation ON nomina_plantillas;

-- Eliminar tablas (en orden inverso por dependencias)
DROP TABLE IF EXISTS nomina_conceptos CASCADE;
DROP TABLE IF EXISTS nomina_plantillas CASCADE;
DROP TABLE IF EXISTS nominas CASCADE;

-- Eliminar tipos ENUM
DROP TYPE IF EXISTS nomina_tipo CASCADE;
DROP TYPE IF EXISTS nomina_status CASCADE;

-- Log de rollback
DO $$
BEGIN
    RAISE NOTICE 'Rollback de migración 2025-11-03_201_hr_nominas completado';
END $$;
